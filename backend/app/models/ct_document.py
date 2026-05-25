"""
CT-e (Electronic Transport Document) models
"""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, String, Integer, DateTime, Numeric, Date, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship

from app.core.database import Base

class CTDocument(Base):
    """
    CT-e document (transport document)
    """
    __tablename__ = "ct_documents"
    __table_args__ = (
        Index("ix_chave_acesso_cte", "chave_acesso"),
        Index("ix_tenant_chave_cte", "tenant_id", "chave_acesso"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)

    # CT-e identification
    chave_acesso = Column(String(44), unique=True, nullable=True, index=True)
    numero_cte = Column(String(20), nullable=False)
    serie = Column(String(20), nullable=False)

    # Parties
    transportador_cnpj = Column(String(14), nullable=False)
    transportador_nome = Column(String(255))
    remetente_cnpj = Column(String(14), nullable=True)
    destinatario_cnpj = Column(String(14), nullable=True)

    # Document details
    data_emissao = Column(Date, nullable=False)
    natureza_operacao = Column(String(50))  # TT (totalizador), CTE (transporte)

    # Financial
    valor_total = Column(Numeric(15, 2), nullable=False)

    # CT-e specific
    status_cte = Column(String(50), nullable=True)  # autorizado, cancelado, denegado
    protocolo_cte = Column(String(50), nullable=True)
    data_autorizacao = Column(DateTime, nullable=True)

    # Versioning
    document_version = Column(Integer, default=1)
    superseded = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="ct_documents")

    def __repr__(self):
        return f"<CTDocument(id={self.id}, chave={self.chave_acesso}, status={self.status_cte})>"

    class Config:
        from_attributes = True
