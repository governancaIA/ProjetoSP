"""
TenantConfig model — per-tenant fiscal configuration stored in public schema.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Index, UniqueConstraint
from app.core.database import Base


class TenantConfig(Base):
    """
    Fiscal configuration for a tenant. Lives in the public schema (shared),
    not inside the tenant's isolated schema. One row per tenant.

    regime_tributario values: "lucro_real", "lucro_presumido", "simples_nacional"
    """
    __tablename__ = "tenant_configs"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_config_tenant_id"),
        Index("ix_tenant_config_tenant_id", "tenant_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, unique=True, index=True)

    # Fiscal identity
    cnpj_principal = Column(String(14), nullable=True)
    razao_social = Column(String(255), nullable=True)
    uf = Column(String(2), nullable=True)  # UF do estabelecimento principal

    # Regime tributário — drives CST and PIS/COFINS validation rules
    regime_tributario = Column(String(50), nullable=True)  # lucro_real | lucro_presumido | simples_nacional

    # Rule tolerance overrides (null = use system defaults)
    tolerance_brl = Column(Numeric(10, 2), nullable=True)  # override for nfe_valor_divergente

    # Onboarding state
    onboarding_completed = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<TenantConfig(tenant_id={self.tenant_id}, regime={self.regime_tributario})>"
