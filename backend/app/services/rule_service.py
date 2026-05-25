"""
Rule service for persistence and configuration management
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import logging

from app.models.rule_log import RuleExecutionLog, SeverityLevel
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
        # MVP: return defaults for all tenants
        # TODO: Load from DB when rule_configurations table is created
        return RuleService.DEFAULT_CONFIG.copy()
