"""
Scoring service for fiscal risk assessment and alert prioritization
Transforms raw rule results into actionable risk scores and financial exposure estimates.
"""
from decimal import Decimal
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
import logging

from app.models.rule_log import RuleExecutionLog, SeverityLevel
from app.models.fiscal_document import FiscalDocument

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity classification for user prioritization"""
    CRITICAL = "CRITICAL"  # Potential fine >R$10k or willful violation
    HIGH = "HIGH"  # Significant divergence (R$1k-R$10k exposure)
    MEDIUM = "MEDIUM"  # Moderate divergence (R$100-R$1k exposure)
    LOW = "LOW"  # Minor issue (<R$100 exposure)
    INFORMATIVE = "INFORMATIVE"  # Pass or informational (no action needed)


class ScoringService:
    """
    Service for calculating fiscal risk scores based on rule execution results.

    Scoring model:
    1. Per-alert score: RuleExecutionLog severity -> AlertSeverity + exposure in R$
    2. Per-document score: aggregate of all alerts for that document
    3. Per-period score: 0-100 scale for a competência (month)
    4. Trend: month-over-month evolution
    """

    # Penalty estimation: DL 1598 art. 12, Portaria CAT
    # These are conservative estimates; actual penalties vary by case
    PENALTY_BASE_RATES = {
        "nfe_valor_divergente": {
            "rate": Decimal("0.75"),  # 75% of diverged amount
            "min": Decimal("500.00"),
            "max": Decimal("10000.00"),
        },
        "nfe_cancelada_no_sped": {
            "rate": Decimal("1.00"),  # 100% of invoice value
            "min": Decimal("1000.00"),
            "max": Decimal("100000.00"),
        },
        "saida_sem_lancamento": {
            "rate": Decimal("0.75"),
            "min": Decimal("500.00"),
            "max": Decimal("50000.00"),
        },
        "cte_cancelado": {
            "rate": Decimal("1.00"),
            "min": Decimal("1000.00"),
            "max": Decimal("100000.00"),
        },
        "icms_divergente": {
            "rate": Decimal("1.50"),  # 150% of tax divergence
            "min": Decimal("300.00"),
            "max": Decimal("50000.00"),
        },
        "cst_incompativel": {
            "rate": Decimal("0.50"),
            "min": Decimal("200.00"),
            "max": Decimal("10000.00"),
        },
        "cfop_invalido": {
            "rate": Decimal("0.50"),
            "min": Decimal("200.00"),
            "max": Decimal("10000.00"),
        },
    }

    @staticmethod
    def calculate_alert_severity(
        rule_log: RuleExecutionLog,
        fiscal_document: FiscalDocument,
    ) -> tuple[AlertSeverity, Decimal]:
        """
        Calculate alert severity and estimated financial exposure from a rule result.

        Args:
            rule_log: RuleExecutionLog record from rule execution
            fiscal_document: FiscalDocument that the rule ran against

        Returns:
            Tuple of (AlertSeverity, exposure_in_brl)
        """
        # If rule passed, no alert
        if rule_log.passed:
            return (AlertSeverity.INFORMATIVE, Decimal("0.00"))

        # Passed rule = no severity/exposure
        # Failed rules: map RuleLog severity -> AlertSeverity + exposure

        # Retrieve penalty config for this rule
        penalty_config = ScoringService.PENALTY_BASE_RATES.get(
            rule_log.rule_id,
            {
                "rate": Decimal("0.50"),
                "min": Decimal("100.00"),
                "max": Decimal("10000.00"),
            },
        )

        exposure = ScoringService._calculate_exposure(
            rule_log, fiscal_document, penalty_config
        )

        # Map rule severity -> alert severity based on exposure
        if rule_log.severity == SeverityLevel.CRITICAL:
            return (AlertSeverity.CRITICAL, exposure)

        # WARNING rules: map to HIGH/MEDIUM based on exposure
        if exposure >= Decimal("1000.00"):
            return (AlertSeverity.HIGH, exposure)
        elif exposure >= Decimal("100.00"):
            return (AlertSeverity.MEDIUM, exposure)
        else:
            return (AlertSeverity.LOW, exposure)

    @staticmethod
    def _calculate_exposure(
        rule_log: RuleExecutionLog,
        fiscal_document: FiscalDocument,
        penalty_config: dict,
    ) -> Decimal:
        """
        Estimate financial exposure (penalty) for a failed rule.

        Args:
            rule_log: RuleExecutionLog with input_snapshot
            fiscal_document: Source document
            penalty_config: Base rate, min, max from PENALTY_BASE_RATES

        Returns:
            Estimated penalty in R$
        """
        rate = Decimal(str(penalty_config.get("rate", 0.50)))
        min_penalty = Decimal(str(penalty_config.get("min", 100.00)))
        max_penalty = Decimal(str(penalty_config.get("max", 10000.00)))

        # Extract divergence amount from input_snapshot
        snapshot = rule_log.get_input_snapshot()

        # Rule-specific exposure calculation
        if rule_log.rule_id == "nfe_valor_divergente":
            divergence = Decimal(str(snapshot.get("divergencia", 0)))
            exposure = divergence * rate

        elif rule_log.rule_id == "nfe_cancelada_no_sped":
            exposure = Decimal(str(fiscal_document.valor_total or 0)) * rate

        elif rule_log.rule_id == "saida_sem_lancamento":
            exposure = Decimal(str(fiscal_document.valor_total or 0)) * rate

        elif rule_log.rule_id == "cte_cancelado":
            exposure = Decimal(str(fiscal_document.valor_total or 0)) * rate

        elif rule_log.rule_id == "icms_divergente":
            divergence = Decimal(str(snapshot.get("divergencia", 0)))
            exposure = divergence * rate

        elif rule_log.rule_id in ["cst_incompativel", "cfop_invalido"]:
            # No direct monetary value; use invoice value * small rate
            exposure = Decimal(str(fiscal_document.valor_total or 0)) * rate * Decimal("0.10")

        else:
            # Unknown rule; conservative estimate
            exposure = Decimal(str(fiscal_document.valor_total or 0)) * rate * Decimal("0.05")

        # Clamp to min/max
        exposure = max(exposure, min_penalty)
        exposure = min(exposure, max_penalty)

        return exposure.quantize(Decimal("0.01"))

    @staticmethod
    def compute_score_from_loaded(fiscal_doc: "FiscalDocument") -> Dict[str, Any]:
        """
        Compute document score from an already-loaded FiscalDocument with preloaded rule_logs.
        Avoids extra DB queries — caller must eager-load rule_logs before calling this.
        """
        alerts_by_severity = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 0,
            AlertSeverity.MEDIUM: 0,
            AlertSeverity.LOW: 0,
            AlertSeverity.INFORMATIVE: 0,
        }
        total_exposure = Decimal("0.00")
        rules_failed = 0
        rules_passed = 0

        for log in fiscal_doc.rule_logs:
            severity, exposure = ScoringService.calculate_alert_severity(log, fiscal_doc)
            alerts_by_severity[severity] += 1
            total_exposure += exposure
            if log.passed:
                rules_passed += 1
            else:
                rules_failed += 1

        score = 100
        score -= alerts_by_severity[AlertSeverity.CRITICAL] * 40
        score -= alerts_by_severity[AlertSeverity.HIGH] * 15
        score -= alerts_by_severity[AlertSeverity.MEDIUM] * 5
        score -= alerts_by_severity[AlertSeverity.LOW] * 1
        score = max(0, min(100, score))

        return {
            "fiscal_document_id": fiscal_doc.id,
            "alerts_by_severity": {k.value: v for k, v in alerts_by_severity.items()},
            "total_exposure": float(total_exposure),
            "document_score": int(score),
            "rules_failed": rules_failed,
            "rules_passed": rules_passed,
            "total_rules": len(fiscal_doc.rule_logs),
        }

    @staticmethod
    def get_document_score(
        db: Session,
        fiscal_document_id: int,
    ) -> Dict[str, Any]:
        """
        Calculate overall score for a single fiscal document.

        Aggregates all rule results into a single risk profile.

        Args:
            db: SQLAlchemy session
            fiscal_document_id: FiscalDocument ID

        Returns:
            Dict with:
              - alerts_by_severity: count of CRITICAL/HIGH/MEDIUM/LOW
              - total_exposure: sum of all estimated penalties
              - document_score: 0-100 representing risk level
              - rules_failed: count of failed rules
              - rules_passed: count of passed rules
        """
        # Fetch document
        from app.models.fiscal_document import FiscalDocument

        fiscal_doc = db.query(FiscalDocument).filter_by(id=fiscal_document_id).first()
        if not fiscal_doc:
            return {"error": f"FiscalDocument {fiscal_document_id} not found"}

        # Single query for this document's logs — no N+1: fiscal_doc is already
        # fetched above and passed directly to calculate_alert_severity().
        rule_logs = (
            db.query(RuleExecutionLog)
            .filter_by(fiscal_document_id=fiscal_document_id)
            .all()
        )

        # Calculate per-alert severity and exposure
        alerts_by_severity = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 0,
            AlertSeverity.MEDIUM: 0,
            AlertSeverity.LOW: 0,
            AlertSeverity.INFORMATIVE: 0,
        }
        total_exposure = Decimal("0.00")
        rules_failed = 0
        rules_passed = 0

        for log in rule_logs:
            severity, exposure = ScoringService.calculate_alert_severity(log, fiscal_doc)
            alerts_by_severity[severity] += 1
            total_exposure += exposure

            if log.passed:
                rules_passed += 1
            else:
                rules_failed += 1

        # Calculate document score (0-100 scale)
        # Heuristic: score based on number of critical issues and total exposure
        # CRITICAL: -40 each, HIGH: -15 each, MEDIUM: -5 each, LOW: -1 each
        score = 100
        score -= alerts_by_severity[AlertSeverity.CRITICAL] * 40
        score -= alerts_by_severity[AlertSeverity.HIGH] * 15
        score -= alerts_by_severity[AlertSeverity.MEDIUM] * 5
        score -= alerts_by_severity[AlertSeverity.LOW] * 1
        score = max(0, min(100, score))  # Clamp to 0-100

        return {
            "fiscal_document_id": fiscal_document_id,
            "alerts_by_severity": {k.value: v for k, v in alerts_by_severity.items()},
            "total_exposure": float(total_exposure),
            "document_score": int(score),
            "rules_failed": rules_failed,
            "rules_passed": rules_passed,
            "total_rules": len(rule_logs),
        }

    @staticmethod
    def get_period_score(
        db: Session,
        tenant_id: str,
        fiscal_year: int,
        fiscal_month: int,
    ) -> Dict[str, Any]:
        """
        Calculate aggregate risk score for a competência (fiscal month).

        Args:
            db: SQLAlchemy session
            tenant_id: Organization ID
            fiscal_year: Year (YYYY)
            fiscal_month: Month (1-12)

        Returns:
            Dict with period-level aggregation:
              - period: "YYYY-MM"
              - documents_processed: count
              - critical_documents: count of docs with >0 CRITICAL alerts
              - period_score: 0-100 aggregate
              - total_exposure: sum of all document exposures
              - top_3_rules: most common failed rules
        """
        from app.models.fiscal_document import FiscalDocument

        # Calculate period date range (fiscal month = calendar month for MVP)
        start_date = date(fiscal_year, fiscal_month, 1)
        if fiscal_month == 12:
            end_date = date(fiscal_year + 1, 1, 1)
        else:
            end_date = date(fiscal_year, fiscal_month + 1, 1)

        # Single query with eager-loaded rule_logs — eliminates N+1
        from sqlalchemy.orm import joinedload
        fiscal_docs = (
            db.query(FiscalDocument)
            .options(joinedload(FiscalDocument.rule_logs))
            .filter(
                FiscalDocument.tenant_id == tenant_id,
                FiscalDocument.data_emissao >= start_date.replace(day=1),
                FiscalDocument.data_emissao < end_date.replace(day=1),
            )
            .all()
        )

        if not fiscal_docs:
            return {
                "period": f"{fiscal_year:04d}-{fiscal_month:02d}",
                "documents_processed": 0,
                "critical_documents": 0,
                "period_score": 100,
                "total_exposure": 0.00,
                "top_3_rules": [],
            }

        # Aggregate scores using pre-loaded rule_logs (no extra queries)
        total_exposure = Decimal("0.00")
        critical_documents = 0
        rule_failure_count = {}
        all_alerts_by_severity = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 0,
            AlertSeverity.MEDIUM: 0,
            AlertSeverity.LOW: 0,
        }

        for doc in fiscal_docs:
            doc_has_critical = False
            for log in doc.rule_logs:
                if not log.passed:
                    rule_failure_count[log.rule_id] = rule_failure_count.get(log.rule_id, 0) + 1
                    severity, exposure = ScoringService.calculate_alert_severity(log, doc)
                    total_exposure += exposure
                    if severity == AlertSeverity.CRITICAL:
                        doc_has_critical = True
                    if severity != AlertSeverity.INFORMATIVE:
                        all_alerts_by_severity[severity] = all_alerts_by_severity.get(severity, 0) + 1
            if doc_has_critical:
                critical_documents += 1

        # Calculate period score
        period_score = 100
        period_score -= all_alerts_by_severity[AlertSeverity.CRITICAL] * 2
        period_score -= all_alerts_by_severity[AlertSeverity.HIGH] * 1
        period_score -= all_alerts_by_severity[AlertSeverity.MEDIUM] * 0.25
        period_score = max(0, min(100, int(period_score)))

        # Top 3 failed rules
        top_3_rules = sorted(
            rule_failure_count.items(), key=lambda x: x[1], reverse=True
        )[:3]

        return {
            "period": f"{fiscal_year:04d}-{fiscal_month:02d}",
            "documents_processed": len(fiscal_docs),
            "critical_documents": critical_documents,
            "period_score": period_score,
            "total_exposure": float(total_exposure),
            "top_3_rules": [{"rule_id": r, "failures": c} for r, c in top_3_rules],
            "alerts_by_severity": {k.value: v for k, v in all_alerts_by_severity.items()},
        }

    @staticmethod
    def get_alert_prioritization_queue(
        db: Session,
        tenant_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get prioritized list of alerts for action queue.

        Orders by: severity × exposure × likelihood (heuristic: document_count)

        Args:
            db: SQLAlchemy session
            tenant_id: Organization ID
            limit: Max number of alerts to return

        Returns:
            List of alerts sorted by priority (highest first)
        """
        from app.models.fiscal_document import FiscalDocument
        from sqlalchemy.orm import joinedload

        # Single query: failed logs with their documents pre-loaded (no N+1)
        rule_logs = (
            db.query(RuleExecutionLog)
            .options(joinedload(RuleExecutionLog.fiscal_document))
            .filter(RuleExecutionLog.tenant_id == tenant_id, RuleExecutionLog.passed == False)
            .all()
        )

        alerts = []
        for log in rule_logs:
            fiscal_doc = log.fiscal_document
            if not fiscal_doc:
                continue

            severity, exposure = ScoringService.calculate_alert_severity(log, fiscal_doc)

            # Priority score: severity weight × exposure × document frequency heuristic
            severity_weight = {
                AlertSeverity.CRITICAL: 4,
                AlertSeverity.HIGH: 3,
                AlertSeverity.MEDIUM: 2,
                AlertSeverity.LOW: 1,
                AlertSeverity.INFORMATIVE: 0,
            }.get(severity, 0)

            priority_score = float(severity_weight * exposure)

            alerts.append(
                {
                    "rule_id": log.rule_id,
                    "rule_version": log.rule_version,
                    "severity": severity.value,
                    "fiscal_document_id": log.fiscal_document_id,
                    "document_chave": fiscal_doc.chave_acesso,
                    "document_value": float(fiscal_doc.valor_total or 0),
                    "exposure": float(exposure),
                    "priority_score": priority_score,
                    "message": log.message,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
            )

        # Sort by priority score descending
        alerts.sort(key=lambda x: x["priority_score"], reverse=True)

        return alerts[:limit]
