"""
Fornecedor (supplier) analytics endpoints — Epic 3 (anomaly detection).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.fiscal_document import FiscalDocument
from app.models.rule_log import RuleExecutionLog
from app.core.security import mask_cnpj

router = APIRouter(prefix="/fornecedores", tags=["fornecedores"])


@router.get("/ranking")
async def get_fornecedor_ranking(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ranking de confiabilidade fiscal por fornecedor (emitente CNPJ).

    Returns suppliers ranked by failure_rate DESC (worst first).
    CNPJs are masked per LGPD — only first 8 digits visible.

    Each entry:
      - emitente_cnpj_masked: masked CNPJ (LGPD)
      - emitente_nome: supplier name
      - total_nfs: total fiscal documents
      - docs_com_falha: documents with ≥1 failed rule
      - failure_rate: docs_com_falha / total_nfs (0.0–1.0)
      - total_exposure: sum of estimated penalties (R$)
    """
    tenant_id = current_user.tenant_id

    # Subquery: which fiscal_document_ids have at least one failed rule
    failed_doc_ids = (
        db.query(RuleExecutionLog.fiscal_document_id)
        .filter(
            RuleExecutionLog.tenant_id == tenant_id,
            RuleExecutionLog.passed == False,  # noqa: E712
        )
        .distinct()
        .subquery()
    )

    # Aggregate by emitente
    rows = (
        db.query(
            FiscalDocument.emitente_cnpj,
            FiscalDocument.emitente_nome,
            func.count(FiscalDocument.id).label("total_nfs"),
            func.sum(
                case((FiscalDocument.id.in_(failed_doc_ids), 1), else_=0)
            ).label("docs_com_falha"),
            func.sum(FiscalDocument.valor_total).label("total_valor"),
        )
        .filter(
            FiscalDocument.tenant_id == tenant_id,
            FiscalDocument.superseded == False,  # noqa: E712
            FiscalDocument.emitente_cnpj.isnot(None),
        )
        .group_by(FiscalDocument.emitente_cnpj, FiscalDocument.emitente_nome)
        .all()
    )

    result = []
    for row in rows:
        total = row.total_nfs or 0
        failed = int(row.docs_com_falha or 0)
        failure_rate = round(failed / total, 4) if total > 0 else 0.0
        result.append({
            "emitente_cnpj_masked": mask_cnpj(row.emitente_cnpj),
            "emitente_nome": row.emitente_nome or "–",
            "total_nfs": total,
            "docs_com_falha": failed,
            "failure_rate": failure_rate,
            "total_valor": float(row.total_valor or 0),
        })

    # Sort worst first, then cap
    result.sort(key=lambda x: (-x["failure_rate"], -x["docs_com_falha"]))
    return result[:limit]
