"""
Audit log model — append-only record of all user actions.
LGPD Art. 37: controller must maintain records of personal data processing operations.
This table is NEVER soft-deleted; retention is governed by TenantConfig.data_retention_years.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Index
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_tenant_ts", "tenant_id", "created_at"),
        Index("ix_audit_user_ts", "user_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False)
    user_id = Column(Integer, nullable=True)   # null for unauthenticated (register, login)
    request_id = Column(String(36), nullable=True)
    ip_address = Column(String(45), nullable=True)  # supports IPv6
    method = Column(String(10), nullable=False)
    path = Column(String(512), nullable=False)
    status_code = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    extra = Column(Text, nullable=True)         # JSON blob, PII-free
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
