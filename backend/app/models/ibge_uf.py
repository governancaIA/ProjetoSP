"""
IBGE UF reference table — 27 states + DF.
Lives in the public schema (shared across all tenants).
"""
from sqlalchemy import Column, String, Integer, Boolean
from app.core.database import Base


class IbgeUf(Base):
    """
    Brazilian state codes per IBGE tabela de UFs.
    Used for validating chave_acesso (positions 1-2 = IBGE UF code)
    and for CFOP inter/intraestadual classification.
    """
    __tablename__ = "ibge_uf"

    codigo_ibge = Column(Integer, primary_key=True)   # 2-digit code (e.g. 35 = SP)
    uf = Column(String(2), nullable=False, unique=True, index=True)
    nome = Column(String(50), nullable=False)
    regiao = Column(String(2), nullable=False)         # N, NE, CO, SE, S
    ativo = Column(Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<IbgeUf(uf={self.uf}, codigo={self.codigo_ibge})>"
