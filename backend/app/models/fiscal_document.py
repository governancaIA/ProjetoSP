"""
Fiscal document models (normalized documents from SPED/NF-e)
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, String, Integer, DateTime, Numeric, Date, ForeignKey, Boolean, Text, Index
from sqlalchemy.orm import relationship

from app.core.database import Base

class FiscalDocument(Base):
    """
    Normalized fiscal document (from SPED C100 or NF-e)
    """
    __tablename__ = "fiscal_documents"
    __table_args__ = (
        Index("ix_chave_acesso", "chave_acesso"),
        Index("ix_tenant_chave", "tenant_id", "chave_acesso"),
        Index("ix_emitente_data", "emitente_cnpj", "data_emissao"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)

    # NF-e identification
    chave_acesso = Column(String(44), unique=True, nullable=True, index=True)  # 35 digits + 9 for extensions
    numero_nf = Column(String(20), nullable=False)
    serie = Column(String(20), nullable=False)

    # Parties
    emitente_cnpj = Column(String(14), nullable=False, index=True)
    emitente_nome = Column(String(255))
    destinatario_cnpj = Column(String(14), nullable=True)
    destinatario_nome = Column(String(255), nullable=True)

    # Document details
    data_emissao = Column(Date, nullable=False, index=True)
    data_saida = Column(Date, nullable=True)
    natureza = Column(String(50))  # saída, entrada, devolução, complementar

    # Financial
    valor_total = Column(Numeric(15, 2), nullable=False)
    valor_icms = Column(Numeric(15, 2), default=Decimal("0.00"))
    valor_pis = Column(Numeric(15, 2), default=Decimal("0.00"))
    valor_cofins = Column(Numeric(15, 2), default=Decimal("0.00"))
    valor_ipi = Column(Numeric(15, 2), default=Decimal("0.00"))

    # NF-e specific
    status_nfe = Column(String(50), nullable=True)  # autorizado, cancelado, denegado
    protocolo_nfe = Column(String(50), nullable=True)
    data_autorizacao = Column(DateTime, nullable=True)

    # Reference (for complement/devolução)
    chave_acesso_referenciada = Column(String(44), nullable=True)

    # Versioning
    document_version = Column(Integer, default=1)
    superseded = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="fiscal_documents")
    items = relationship("FiscalItem", back_populates="fiscal_document")
    rule_logs = relationship("RuleExecutionLog", back_populates="fiscal_document")

    def __repr__(self):
        return f"<FiscalDocument(id={self.id}, chave={self.chave_acesso}, status={self.status_nfe})>"

    class Config:
        from_attributes = True

class FiscalItem(Base):
    """
    Items within a fiscal document (from SPED C170)
    """
    __tablename__ = "fiscal_items"
    __table_args__ = (
        Index("ix_fiscal_doc_seq", "fiscal_document_id", "item_seq"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    fiscal_document_id = Column(Integer, ForeignKey("fiscal_documents.id"), nullable=False)

    # Item sequence
    item_seq = Column(Integer, nullable=False)

    # Product
    codigo_produto = Column(String(60), nullable=True)
    descricao = Column(String(255))
    ncm = Column(String(8), nullable=True)

    # Operation
    cfop = Column(String(4), nullable=False)
    cst = Column(String(3), nullable=False)  # Simples Nacional CSTs have 3 digits (101, 102…)

    # Quantity
    quantidade = Column(Numeric(15, 4), nullable=False)
    unidade = Column(String(5), nullable=True)

    # Financial
    valor_unitario = Column(Numeric(15, 2), nullable=False)
    valor_item = Column(Numeric(15, 2), nullable=False)
    valor_desconto = Column(Numeric(15, 2), default=Decimal("0.00"))

    # Taxes - Base calculations
    base_icms = Column(Numeric(15, 2), default=Decimal("0.00"))
    aliquota_icms = Column(Numeric(5, 2), default=Decimal("0.00"))
    valor_icms = Column(Numeric(15, 2), default=Decimal("0.00"))

    base_pis = Column(Numeric(15, 2), default=Decimal("0.00"))
    aliquota_pis = Column(Numeric(5, 2), default=Decimal("0.00"))
    valor_pis = Column(Numeric(15, 2), default=Decimal("0.00"))

    base_cofins = Column(Numeric(15, 2), default=Decimal("0.00"))
    aliquota_cofins = Column(Numeric(5, 2), default=Decimal("0.00"))
    valor_cofins = Column(Numeric(15, 2), default=Decimal("0.00"))

    valor_ipi = Column(Numeric(15, 2), default=Decimal("0.00"))

    # Versioning
    document_version = Column(Integer, default=1)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    fiscal_document = relationship("FiscalDocument", back_populates="items")

    def __repr__(self):
        return f"<FiscalItem(id={self.id}, doc_id={self.fiscal_document_id}, seq={self.item_seq})>"

    class Config:
        from_attributes = True
