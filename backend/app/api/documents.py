"""
Document list endpoint
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.fiscal_document import FiscalDocument
from app.schemas.documents import DocumentsResponse, DocumentListItem
from app.services.scoring_service import ScoringService

router = APIRouter()


@router.get("/documents", response_model=DocumentsResponse)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
):
    """
    List all documents for current tenant

    Returns active (non-superseded) documents with basic info and score
    """
    tenant_id = current_user.tenant_id

    # Query fiscal documents for this tenant (non-superseded only), eager-loading
    # rule_logs to avoid N+1 queries when computing scores
    base_filter = and_(
        FiscalDocument.tenant_id == tenant_id,
        FiscalDocument.superseded == False,
    )
    total = db.query(FiscalDocument).filter(base_filter).count()
    documents = (
        db.query(FiscalDocument)
        .filter(base_filter)
        .options(joinedload(FiscalDocument.rule_logs))
        .order_by(FiscalDocument.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Build response items
    items = []
    for doc in documents:
        score = ScoringService.compute_score_from_loaded(doc)

        item = DocumentListItem(
            id=doc.id,
            chave_acesso=doc.chave_acesso,
            numero_nf=doc.numero_nf,
            emitente_nome=doc.emitente_nome,
            data_emissao=doc.data_emissao,
            status_nfe=doc.status_nfe,
            valor_total=doc.valor_total,
            document_score=score.get("document_score", 0),
        )
        items.append(item)

    return DocumentsResponse(documents=items, total=total)
