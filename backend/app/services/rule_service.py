"""
Rule service for persistence and configuration management
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging

from app.models.rule_log import RuleExecutionLog, SeverityLevel
from app.models.tenant_config import TenantConfig
from app.models.cfop_reference import CfopReference
from app.models.cst_icms_reference import CstIcmsReference
from app.validators.rules.base import RuleResult


logger = logging.getLogger(__name__)


class RuleServiceError(Exception):
    """Rule service error"""
    pass


class RuleService:
    """
    Service for persisting rule execution results and managing rule configurations.
    """

    DEFAULT_CONFIG = {
        "tolerance_brl": 0.01,  # R$0.01 default tolerance for monetary comparisons
        "regime_tributario": None,  # populated from TenantConfig when available
    }

    @staticmethod
    def save_results(
        db: Session,
        tenant_id: str,
        fiscal_document_id: int,
        results: List[RuleResult],
        triggered_by: str,
    ) -> List[RuleExecutionLog]:
        """
        Persist a list of RuleResult objects as RuleExecutionLog records.

        Args:
            db: SQLAlchemy session
            tenant_id: Organization/tenant ID
            fiscal_document_id: Parent FiscalDocument ID
            results: List of RuleResult objects to persist
            triggered_by: Trigger source (e.g., "parser", "reprocess", "manual_validation")

        Returns:
            List of persisted RuleExecutionLog instances

        Raises:
            RuleServiceError: If save fails
        """
        try:
            logs = []
            for result in results:
                log = RuleExecutionLog(
                    tenant_id=tenant_id,
                    fiscal_document_id=fiscal_document_id,
                    rule_id=result.rule_id,
                    rule_version=result.rule_version,
                    passed=result.passed,
                    severity=result.severity,
                    message=result.message,
                    input_snapshot=result.input_snapshot,
                    config_applied=result.config_applied,
                    triggered_by=triggered_by,
                )
                db.add(log)
                logs.append(log)

            logger.info(
                f"Saved {len(logs)} rule execution logs for fiscal_document={fiscal_document_id}"
            )
            return logs

        except Exception as e:
            logger.error(f"Failed to save rule execution logs: {str(e)}")
            raise RuleServiceError(f"Failed to save rule logs: {str(e)}")

    @staticmethod
    def get_config(
        db: Session,
        tenant_id: str,
        rule_id: str,
    ) -> Dict[str, Any]:
        """
        Get rule configuration for a tenant.

        For MVP, this returns DEFAULT_CONFIG. Future versions will:
        - Load from `rule_configurations` table
        - Support per-tenant overrides
        - Cache in Redis

        Args:
            db: SQLAlchemy session (for future DB queries)
            tenant_id: Organization/tenant ID
            rule_id: Rule identifier (or "*" for all rules)

        Returns:
            Configuration dict with tolerance and other settings
        """
        config = RuleService.DEFAULT_CONFIG.copy()

        # Load tenant-specific overrides from TenantConfig (public schema)
        tenant_cfg = db.query(TenantConfig).filter_by(tenant_id=tenant_id).first()
        if tenant_cfg:
            if tenant_cfg.regime_tributario:
                config["regime_tributario"] = tenant_cfg.regime_tributario
            if tenant_cfg.tolerance_brl is not None:
                config["tolerance_brl"] = float(tenant_cfg.tolerance_brl)

        # Load valid CFOPs from reference table (public schema, ADE COTEPE)
        cfop_rows = db.query(CfopReference).filter_by(ativo=True).all()
        if cfop_rows:
            config["valid_cfops"] = {row.cfop for row in cfop_rows}
            config["cfop_metadata"] = {
                row.cfop: {
                    "tipo_operacao": row.tipo_operacao,
                    "escopo": row.escopo,
                    "permite_devolucao": row.permite_devolucao,
                }
                for row in cfop_rows
            }

        # Load valid CSTs from reference table (public schema, Anexo I Conv. S/N)
        cst_rows = db.query(CstIcmsReference).filter_by(ativo=True).all()
        if cst_rows:
            regime = config.get("regime_tributario", "")
            regime_col_map = {
                "lucro_real": "regime_lucro_real",
                "lucro_presumido": "regime_lucro_presumido",
                "simples_nacional": "regime_simples",
            }
            col_name = regime_col_map.get(regime) if regime else None

            config["valid_csts_all"] = {row.cst for row in cst_rows}
            if col_name:
                config["valid_csts_regime"] = {
                    row.cst for row in cst_rows if getattr(row, col_name)
                }

        return config
