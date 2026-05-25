"""
Validation and scoring endpoints (US-2.1, US-4.1)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db, set_tenant_schema
from app.api.deps import get_current_user
from app.models.user import User
from app.services.scoring_service import ScoringService

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
    # Extract tenant_id from current user
    tenant_id = current_user.tenant_id

    # Set tenant schema for query
    set_tenant_schema(db, tenant_id)

    try:
        result = ScoringService.get_period_score(db, tenant_id, fiscal_year, fiscal_month)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    # Extract tenant_id from current user
    tenant_id = current_user.tenant_id

    # Set tenant schema for query
    set_tenant_schema(db, tenant_id)

    try:
        alerts = ScoringService.get_alert_prioritization_queue(db, tenant_id, limit=limit)
        return {"alerts": alerts, "total": len(alerts)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
