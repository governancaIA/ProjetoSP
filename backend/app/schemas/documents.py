"""
Schemas for document and validation endpoints
"""
from decimal import Decimal
from datetime import date, datetime
from pydantic import BaseModel, Field
from typing import Optional, List


# ── Document List Response ────────────────────────────────────────────────────

class DocumentListItem(BaseModel):
    """Document item for list view"""
    document_id: int = Field(..., alias="id")
    chave_acesso: Optional[str] = None
    numero_nf: str
    emitente_nome: Optional[str] = None
    data_emissao: date
    status_nfe: Optional[str] = None
    valor_total: Decimal
    document_score: Optional[float] = None

    class Config:
        from_attributes = True


class DocumentsResponse(BaseModel):
    """List of documents for current tenant"""
    documents: List[DocumentListItem]
    total: int = Field(default=0)


# ── Document Detail Response ──────────────────────────────────────────────────

class DocumentDetailResponse(BaseModel):
    """Detailed document information"""
    document_id: int = Field(..., alias="id")
    chave_acesso: Optional[str] = None
    numero_nf: str
    serie: str

    # Parties
    emitente_cnpj: str
    emitente_nome: Optional[str] = None
    destinatario_cnpj: Optional[str] = None
    destinatario_nome: Optional[str] = None

    # Dates
    data_emissao: date
    data_saida: Optional[date] = None

    # Financials
    valor_total: Decimal
    valor_icms: Decimal
    valor_pis: Decimal
    valor_cofins: Decimal
    valor_ipi: Decimal

    # NF-e Status
    status_nfe: Optional[str] = None
    protocolo_nfe: Optional[str] = None

    # Metadata
    natureza: Optional[str] = None
    document_version: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Validation Results ─────────────────────────────────────────────────────

class ValidationResultItem(BaseModel):
    """Single rule validation result"""
    rule_id: str
    rule_version: str
    passed: bool
    severity: Optional[str] = None  # CRITICAL, WARNING, INFO
    message: Optional[str] = None
    triggered_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentValidationResponse(BaseModel):
    """Validation results for a document"""
    document_id: int
    results: List[ValidationResultItem]


# ── Document Score ────────────────────────────────────────────────────────

class DocumentScoreResponse(BaseModel):
    """Risk score for a single document"""
    fiscal_document_id: int
    alerts_by_severity: dict[str, int] = Field(
        default={
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "INFORMATIVE": 0,
        }
    )
    total_exposure: float
    document_score: float  # 0-100
    rules_failed: int
    rules_passed: int
    total_rules: int
