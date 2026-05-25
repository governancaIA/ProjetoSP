"""
Rule execution log models (Epic 2 - Validation Rules)
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
import enum
import json

from app.core.database import Base

class SeverityLevel(str, enum.Enum):
    """Rule result severity levels"""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"

class RuleExecutionLog(Base):
    """
    Log of rule execution results for audit trail
    """
    __tablename__ = "fiscal_rules_log"
    __table_args__ = (
        Index("ix_doc_id", "fiscal_document_id"),
        Index("ix_doc_rule", "fiscal_document_id", "rule_id"),
        Index("ix_created", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    fiscal_document_id = Column(Integer, ForeignKey("fiscal_documents.id"), nullable=False)

    # Rule information
    rule_id = Column(String(100), nullable=False, index=True)  # "nfe_vs_sped_divergence"
    rule_version = Column(String(20), nullable=False)  # "1.0.0"

    # Result
    passed = Column(Boolean, nullable=False)
    severity = Column(Enum(SeverityLevel), nullable=False)
    message = Column(Text)  # Human-readable message in PT-BR

    # Audit data
    input_snapshot = Column(JSON, nullable=True)  # Actual values that were compared
    config_applied = Column(JSON, nullable=True)  # Tolerances/settings used
    triggered_by = Column(String(50), nullable=False)  # "parser", "reprocess", "manual_validation"

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    fiscal_document = relationship("FiscalDocument", back_populates="rule_logs")

    def __repr__(self):
        return f"<RuleExecutionLog(id={self.id}, rule={self.rule_id}, passed={self.passed})>"

    class Config:
        from_attributes = True

    def get_input_snapshot(self) -> dict:
        """Safely retrieve input snapshot as dict"""
        if isinstance(self.input_snapshot, str):
            return json.loads(self.input_snapshot)
        return self.input_snapshot or {}

    def get_config_applied(self) -> dict:
        """Safely retrieve config applied as dict"""
        if isinstance(self.config_applied, str):
            return json.loads(self.config_applied)
        return self.config_applied or {}
