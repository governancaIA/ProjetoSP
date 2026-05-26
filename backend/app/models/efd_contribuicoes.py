"""
EFD Contribuições model — normalized PIS/COFINS apuração per period.
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class EFDContribuicoes(Base):
    """
    Summarized PIS and COFINS apuração extracted from an EFD Contribuições file.
    One row per (tenant, document, period) — sourced from M200/M500 totals.
    Detail by CST is stored in EFDContribuicoesCst (M100/M400 rows).
    """
    __tablename__ = "efd_contribuicoes"
    __table_args__ = (
        Index("ix_efd_contrib_tenant_periodo", "tenant_id", "dt_ini"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)

    # Period
    dt_ini = Column(Date, nullable=False)
    dt_fin = Column(Date, nullable=False)

    # Company identification (from 0000)
    cnpj = Column(String(14), nullable=True)
    nome = Column(String(255), nullable=True)
    uf = Column(String(2), nullable=True)
    # EFD Contribuições specific: regime cumulativo (0) or não-cumulativo (1)
    ind_reg_cum = Column(String(1), nullable=True)
    # Tipo de contribuição (1=PIS+COFINS, 2=PIS only, 3=COFINS only)
    cod_tipo_contrib = Column(String(1), nullable=True)

    # PIS totals (M200)
    pis_vl_contrib = Column(Numeric(15, 2), default=Decimal("0.00"))
    pis_vl_cred_desc = Column(Numeric(15, 2), default=Decimal("0.00"))
    pis_vl_saldo_devedor = Column(Numeric(15, 2), default=Decimal("0.00"))

    # COFINS totals (M500)
    cofins_vl_contrib = Column(Numeric(15, 2), default=Decimal("0.00"))
    cofins_vl_cred_desc = Column(Numeric(15, 2), default=Decimal("0.00"))
    cofins_vl_saldo_devedor = Column(Numeric(15, 2), default=Decimal("0.00"))

    created_at = Column(DateTime, default=datetime.utcnow)

    cst_details = relationship("EFDContribuicoesCst", back_populates="efd_contribuicoes")

    def __repr__(self):
        return f"<EFDContribuicoes(tenant={self.tenant_id}, periodo={self.dt_ini})>"


class EFDContribuicoesCst(Base):
    """
    PIS/COFINS detail per CST per period (from M100 and M400 records).
    Enables cst_incompativel rule to have real data.
    """
    __tablename__ = "efd_contribuicoes_cst"
    __table_args__ = (
        Index("ix_efd_cst_efd_id", "efd_contribuicoes_id"),
        Index("ix_efd_cst_tipo_cst", "tipo", "cst"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    efd_contribuicoes_id = Column(Integer, ForeignKey("efd_contribuicoes.id"), nullable=False)

    tipo = Column(String(6), nullable=False)   # "PIS" | "COFINS"
    cst = Column(String(2), nullable=False)
    vl_bc = Column(Numeric(15, 2), default=Decimal("0.00"))
    aliq_perc = Column(Numeric(8, 4), default=Decimal("0.0000"))
    vl_cred = Column(Numeric(15, 2), default=Decimal("0.00"))

    efd_contribuicoes = relationship("EFDContribuicoes", back_populates="cst_details")

    def __repr__(self):
        return f"<EFDContribuicoesCst(tipo={self.tipo}, cst={self.cst}, cred={self.vl_cred})>"
