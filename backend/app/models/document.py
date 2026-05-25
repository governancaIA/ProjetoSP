"""
Document models for fiscal file tracking
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base

class DocumentType(str, enum.Enum):
    """Types of fiscal documents"""
    SPED_EFD_ICMS = "sped_efd_icms"
    EFD_CONTRIBUICOES = "efd_contribuicoes"
    NFE = "nfe"
    CTE = "cte"
    UNKNOWN = "unknown"

class Document(Base):
    """
    Represents an uploaded fiscal document
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)

    # File metadata
    original_filename = Column(String(255), nullable=False)
    document_type = Column(Enum(DocumentType), default=DocumentType.UNKNOWN)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    file_size = Column(Integer, nullable=False)

    # Storage
    storage_key = Column(String(255), nullable=False)  # S3/MinIO key
    storage_bucket = Column(String(100), nullable=False)

    # Versioning
    document_version = Column(Integer, default=1)
    superseded = Column(Boolean, default=False)

    # Status
    processing_status = Column(String(50), default="pending")  # pending, processing, completed, failed
    processing_error = Column(Text, nullable=True)
    celery_task_id = Column(String(255), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    fiscal_documents = relationship("FiscalDocument", back_populates="document")
    ct_documents = relationship("CTDocument", back_populates="document")

    def __repr__(self):
        return f"<Document(id={self.id}, tenant_id={self.tenant_id}, type={self.document_type}, status={self.processing_status})>"

    class Config:
        from_attributes = True
