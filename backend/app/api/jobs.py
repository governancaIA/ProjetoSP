"""
Job status endpoint for polling async task progress
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.document import Document

router = APIRouter()


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    document_id: Optional[int] = None
    original_filename: Optional[str] = None
    document_type: Optional[str] = None
    error: Optional[str] = None


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobStatusResponse:
    """
    Poll async job status for a document upload.

    Returns processing_status from the Document record.
    Frontend polls this endpoint to show real-time progress.
    """
    doc = db.query(Document).filter(
        Document.celery_task_id == job_id,
        Document.tenant_id == current_user.tenant_id,
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    return JobStatusResponse(
        job_id=job_id,
        status=doc.processing_status,
        document_id=doc.id,
        original_filename=doc.original_filename,
        document_type=doc.document_type.value if doc.document_type else None,
        error=doc.processing_error,
    )
