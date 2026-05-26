"""
CFOP reference table — ADE COTEPE vigente.
Lives in the public schema (shared across all tenants).
"""
from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base


class CfopReference(Base):
    """
    All valid CFOPs per ADE COTEPE/ICMS 42/2009 and subsequent updates.

    tipo_operacao: "entrada" | "saida"
    escopo:        "intraestadual" | "interestadual" | "exterior" | "qualquer"
    """
    __tablename__ = "cfop_reference"

    cfop = Column(String(4), primary_key=True)
    descricao = Column(String(255), nullable=False)
    tipo_operacao = Column(String(20), nullable=False)   # entrada | saida
    escopo = Column(String(20), nullable=False)          # intraestadual | interestadual | exterior | qualquer
    permite_devolucao = Column(Boolean, default=False, nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<CfopReference(cfop={self.cfop}, tipo={self.tipo_operacao})>"
