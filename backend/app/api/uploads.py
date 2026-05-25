"""
Upload endpoints for fiscal documents (SPED, NF-e, CT-e, etc)
US-1.1: Upload with validation and checksum
US-1.2: Batch upload and lote processing
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentType
from app.services.storage_service import StorageService, StorageServiceError
from app.services.document_service import DocumentService
from app.tasks.parse_document import parse_document

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed MIME types for fiscal documents
ALLOWED_MIME_TYPES = {
    "text/plain",  # SPED files (.txt)
    "application/xml",  # XML files (NF-e, CT-e)
    "text/xml",  # Variant of XML
}

# Maximum file size: 2 GB (per docs/epics.md requirement)
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB in bytes

# Storage quota per tenant per month: 10GB default
STORAGE_QUOTA_BYTES = 10 * 1024 * 1024 * 1024  # 10GB


class UploadError(Exception):
    """Upload error"""
    pass


@router.post("/uploads", status_code=status.HTTP_201_CREATED)
async def upload_files(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload fiscal documents (SPED, NF-e, CT-e, etc).

    Supports:
    - Multiple files (batch upload)
    - File size up to 2GB
    - Automatic document type detection
    - Checksum validation (SHA-256)
    - Asynchronous parsing via Celery

    Returns:
    - List of upload results with job IDs for tracking

    AC Compliance:
    - Files up to 2GB accepted
    - Checksum SHA-256 validated
    - Progress tracked via job_id
    """
    tenant_id = current_user.tenant_id
    results = []

    try:
        # Validate input
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )

        if len(files) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 files per upload"
            )

        current_usage = _get_tenant_storage_usage(db, tenant_id)
        logger.info(f"Tenant {tenant_id} current usage: {current_usage} bytes")
        storage = None  # Lazy init — only connect to MinIO when needed

        # Process each file
        for file in files:
            try:
                # Validate MIME type
                if file.content_type not in ALLOWED_MIME_TYPES:
                    logger.warning(f"Invalid MIME type: {file.content_type} for {file.filename}")
                    results.append({
                        "filename": file.filename,
                        "status": "rejected",
                        "reason": f"Invalid file type: {file.content_type}. Allowed: {', '.join(ALLOWED_MIME_TYPES)}"
                    })
                    continue

                # Read file content
                content = await file.read()

                # Validate file size
                if len(content) > MAX_FILE_SIZE:
                    logger.warning(f"File too large: {file.filename} ({len(content)} bytes)")
                    results.append({
                        "filename": file.filename,
                        "status": "rejected",
                        "reason": f"File size {len(content)} bytes exceeds 2GB limit"
                    })
                    continue

                # Check storage quota
                new_usage = current_usage + len(content)
                if new_usage > STORAGE_QUOTA_BYTES:
                    logger.warning(f"Storage quota exceeded for {tenant_id}")
                    results.append({
                        "filename": file.filename,
                        "status": "rejected",
                        "reason": f"Storage quota exceeded. Current: {current_usage} bytes, Limit: {STORAGE_QUOTA_BYTES} bytes"
                    })
                    continue

                # Calculate SHA-256 checksum
                file_hash = StorageService.calculate_file_hash(content)
                logger.info(f"Calculated hash: {file_hash} for {file.filename}")

                # Check if file already uploaded (deduplication)
                existing_doc = db.query(Document).filter_by(
                    tenant_id=tenant_id,
                    file_hash=file_hash
                ).first()

                if existing_doc:
                    logger.info(f"File already uploaded: {file.filename} (hash: {file_hash})")
                    results.append({
                        "filename": file.filename,
                        "status": "duplicate",
                        "document_id": existing_doc.id,
                        "message": f"File already uploaded on {existing_doc.created_at.isoformat()}"
                    })
                    continue

                # Upload to MinIO (lazy init on first real upload)
                if storage is None:
                    storage = StorageService()

                storage_key = StorageService.build_storage_key(
                    tenant_id=tenant_id,
                    document_type="unknown",  # Type detected during parsing
                    file_hash=file_hash,
                    ext=_get_file_extension(file.filename)
                )

                try:
                    uploaded_key = storage.upload(
                        content=content,
                        key=storage_key,
                        content_type=file.content_type
                    )
                    logger.info(f"Uploaded to MinIO: {uploaded_key}")
                except StorageServiceError as e:
                    logger.error(f"Storage error: {str(e)}")
                    results.append({
                        "filename": file.filename,
                        "status": "error",
                        "reason": f"Storage error: {str(e)}"
                    })
                    continue

                # Create Document record
                doc = DocumentService.create_document_record(
                    db=db,
                    tenant_id=tenant_id,
                    original_filename=file.filename,
                    document_type=DocumentType.UNKNOWN,  # Type detected during parsing
                    file_hash=file_hash,
                    file_size=len(content),
                    storage_key=storage_key,
                    storage_bucket=storage.bucket,
                )

                db.commit()
                logger.info(f"Created Document record: id={doc.id}")

                # Enqueue parsing task
                task = parse_document.delay(doc.id, tenant_id)
                logger.info(f"Enqueued parse_document task: {task.id} for document {doc.id}")

                results.append({
                    "filename": file.filename,
                    "status": "accepted",
                    "document_id": doc.id,
                    "job_id": task.id,
                    "file_hash": file_hash,
                    "file_size": len(content),
                    "message": "File uploaded and queued for processing"
                })

                # Update current usage
                current_usage = new_usage

            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}", exc_info=True)
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "reason": f"Unexpected error: {str(e)}"
                })

        return {
            "tenant_id": tenant_id,
            "upload_timestamp": __import__('datetime').datetime.utcnow().isoformat(),
            "total_files": len(files),
            "results": results,
            "summary": {
                "accepted": len([r for r in results if r["status"] == "accepted"]),
                "rejected": len([r for r in results if r["status"] == "rejected"]),
                "duplicates": len([r for r in results if r["status"] == "duplicate"]),
                "errors": len([r for r in results if r["status"] == "error"]),
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload_files: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


def _get_file_extension(filename: str) -> str:
    """Extract file extension from filename"""
    if "." in filename:
        return filename.rsplit(".", 1)[1].lower()
    return "txt"


def _get_tenant_storage_usage(db: Session, tenant_id: str) -> int:
    """
    Calculate total storage usage for a tenant.

    Returns:
        Total size of all documents in bytes
    """
    from sqlalchemy import func

    total = db.query(func.sum(Document.file_size)).filter_by(
        tenant_id=tenant_id,
        superseded=False
    ).scalar()

    return total or 0
