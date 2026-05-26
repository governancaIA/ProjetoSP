"""
CST ICMS reference table — Anexo I do Convênio S/N de 1970 e atualizações.
Lives in the public schema (shared across all tenants).
"""
from sqlalchemy import Column, String, Boolean
from app.core.database import Base


class CstIcmsReference(Base):
    """
    Valid ICMS CST codes per regime tributário.

    Tabela A (regime normal — Lucro Real / Lucro Presumido): codes 00–90
    Tabela B (Simples Nacional): codes 101–900
    """
    __tablename__ = "cst_icms_reference"

    cst = Column(String(3), primary_key=True)
    descricao = Column(String(255), nullable=False)
    tabela = Column(String(1), nullable=False)          # "A" | "B"
    regime_lucro_real = Column(Boolean, nullable=False, default=False)
    regime_lucro_presumido = Column(Boolean, nullable=False, default=False)
    regime_simples = Column(Boolean, nullable=False, default=False)
    ativo = Column(Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<CstIcmsReference(cst={self.cst}, tabela={self.tabela})>"
