"""
Validation and scoring endpoints (US-2.1, US-4.1, US-5.2)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, extract
from typing import Optional, List

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.scoring_service import ScoringService, AlertSeverity

router = APIRouter()


@router.get("/documents/{doc_id}/validation-results")
async def get_validation_results(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get validation results (rule execution logs) for a document"""
    from app.models.rule_log import RuleExecutionLog
    from app.models.fiscal_document import FiscalDocument
    from sqlalchemy import and_

    # Verify document belongs to user's tenant
    fiscal_doc = db.query(FiscalDocument).filter(
        and_(
            FiscalDocument.id == doc_id,
            FiscalDocument.tenant_id == current_user.tenant_id,
        )
    ).first()

    if not fiscal_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    logs = db.query(RuleExecutionLog).filter_by(fiscal_document_id=doc_id).all()

    if not logs:
        return {"document_id": doc_id, "results": []}

    return {
        "document_id": doc_id,
        "results": [
            {
                "rule_id": log.rule_id,
                "rule_version": log.rule_version,
                "passed": log.passed,
                "severity": log.severity.value if log.severity else None,
                "message": log.message,
                "triggered_by": log.triggered_by,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }


@router.get("/documents/{doc_id}/score")
async def get_document_score(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get fiscal risk score for a document.

    Returns:
    - alerts_by_severity: count of CRITICAL/HIGH/MEDIUM/LOW alerts
    - total_exposure: estimated financial exposure (penalty) in R$
    - document_score: 0-100 risk score
    - rules_failed: count of failed validation rules
    - rules_passed: count of passed validation rules
    """
    from app.models.fiscal_document import FiscalDocument
    from sqlalchemy import and_

    # Verify document belongs to user's tenant
    fiscal_doc = db.query(FiscalDocument).filter(
        and_(
            FiscalDocument.id == doc_id,
            FiscalDocument.tenant_id == current_user.tenant_id,
        )
    ).first()

    if not fiscal_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        result = ScoringService.get_document_score(db, doc_id)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/periods/{fiscal_year}/{fiscal_month}/score")
async def get_period_score(
    fiscal_year: int,
    fiscal_month: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get aggregate fiscal risk score for a competência (fiscal month).

    Returns:
    - period: "YYYY-MM" format
    - documents_processed: number of documents in period
    - critical_documents: documents with CRITICAL alerts
    - period_score: 0-100 aggregate risk score
    - total_exposure: total estimated penalties for period
    - top_3_rules: most frequently failed rules
    - alerts_by_severity: count by severity level
    """
    tenant_id = current_user.tenant_id

    try:
        result = ScoringService.get_period_score(db, tenant_id, fiscal_year, fiscal_month)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/periods/trend")
async def get_score_trend(
    months: int = Query(default=12, ge=1, le=24),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns period scores for the last N months (oldest → newest).
    Used by the dashboard trend chart.
    """
    try:
        return ScoringService.get_trend(db, current_user.tenant_id, months)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _mask_chave_acesso(chave: str | None) -> str | None:
    """Mask CNPJ digits (positions 7-20) in NF-e access key per LGPD Art. 46."""
    if not chave or len(chave) < 20:
        return chave
    return chave[:6] + "***CNPJ***" + chave[20:]


@router.get("/alerts")
async def list_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    severity: Optional[List[str]] = Query(None),
    rule_id: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    fiscal_month: Optional[int] = None,
    min_exposure: Optional[float] = None,
    max_exposure: Optional[float] = None,
    page: int = 1,
    page_size: int = 50,
):
    """
    List alerts with advanced filters and SQL pagination.

    Severity and exposure are computed in Python (not stored in DB), so
    filtering on those fields happens after SQL fetch, within a page.
    For best results, combine with period/rule filters to narrow the SQL set.
    """
    from app.models.rule_log import RuleExecutionLog
    from app.models.fiscal_document import FiscalDocument

    page_size = min(page_size, 200)
    tenant_id = current_user.tenant_id

    query = (
        db.query(RuleExecutionLog, FiscalDocument)
        .join(FiscalDocument, RuleExecutionLog.fiscal_document_id == FiscalDocument.id)
        .filter(
            RuleExecutionLog.tenant_id == tenant_id,
            RuleExecutionLog.passed == False,
        )
    )

    if rule_id:
        query = query.filter(RuleExecutionLog.rule_id == rule_id)

    if fiscal_year and fiscal_month:
        query = query.filter(
            extract("year", FiscalDocument.data_emissao) == fiscal_year,
            extract("month", FiscalDocument.data_emissao) == fiscal_month,
        )
    elif fiscal_year:
        query = query.filter(extract("year", FiscalDocument.data_emissao) == fiscal_year)

    total_unfiltered = query.count()
    rows = (
        query.order_by(RuleExecutionLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    alerts = []
    for log, doc in rows:
        alert_severity, exposure = ScoringService.calculate_alert_severity(log, doc)

        if severity and alert_severity.value not in severity:
            continue
        if min_exposure is not None and float(exposure) < min_exposure:
            continue
        if max_exposure is not None and float(exposure) > max_exposure:
            continue

        alerts.append({
            "alert_id": log.id,
            "rule_id": log.rule_id,
            "rule_version": log.rule_version,
            "severity": alert_severity.value,
            "fiscal_document_id": doc.id,
            "document_chave": _mask_chave_acesso(doc.chave_acesso),
            "document_value": float(doc.valor_total or 0),
            "emitente_nome": doc.emitente_nome,
            "data_emissao": doc.data_emissao.isoformat() if doc.data_emissao else None,
            "exposure": float(exposure),
            "message": log.message,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return {
        "alerts": alerts,
        "total": total_unfiltered,
        "page": page,
        "page_size": page_size,
        "pages": (total_unfiltered + page_size - 1) // page_size,
    }


@router.get("/alerts/priority-queue")
async def get_priority_queue(
    current_user: User = Depends(get_current_user),
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """
    Get prioritized alert queue for action.

    Alerts are sorted by (severity × exposure), highest priority first.

    Returns:
    - List of alerts with severity, exposure, and priority score
    """
    tenant_id = current_user.tenant_id

    try:
        alerts = ScoringService.get_alert_prioritization_queue(db, tenant_id, limit=limit)
        return {"alerts": alerts, "total": len(alerts)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
