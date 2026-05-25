"""
Base classes for fiscal validation rules
"""
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from decimal import Decimal

from app.models.rule_log import SeverityLevel


@dataclass
class RuleResult:
    """Result of a single rule execution"""
    rule_id: str
    rule_version: str
    passed: bool
    severity: SeverityLevel
    message: str
    input_snapshot: dict = field(default_factory=dict)
    config_applied: dict = field(default_factory=dict)


class BaseRule(ABC):
    """
    Abstract base class for fiscal validation rules.
    Subclasses must implement execute() and set rule_id, rule_version.
    """
    rule_id: str = None
    rule_version: str = None
    depends_on: list[str] = []

    @abstractmethod
    def execute(
        self,
        fiscal_document,
        items: list,
        config: dict,
    ) -> RuleResult:
        """
        Execute the rule against a fiscal document.

        Args:
            fiscal_document: FiscalDocument instance (with chave_acesso, valor_total, etc)
            items: List of FiscalItem instances
            config: Tenant-specific configuration (e.g., {"tolerance_brl": 0.01})

        Returns:
            RuleResult with passed, severity, message, and audit data
        """
        pass

    def _pass(
        self,
        message: str,
        input_snapshot: dict = None,
        config_applied: dict = None,
    ) -> RuleResult:
        """Helper: create a passing result"""
        return RuleResult(
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            passed=True,
            severity=SeverityLevel.INFO,
            message=message,
            input_snapshot=input_snapshot or {},
            config_applied=config_applied or {},
        )

    def _fail(
        self,
        severity: SeverityLevel,
        message: str,
        input_snapshot: dict = None,
        config_applied: dict = None,
    ) -> RuleResult:
        """Helper: create a failing result"""
        return RuleResult(
            rule_id=self.rule_id,
            rule_version=self.rule_version,
            passed=False,
            severity=severity,
            message=message,
            input_snapshot=input_snapshot or {},
            config_applied=config_applied or {},
        )
