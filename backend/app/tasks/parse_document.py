"""
Celery task for document parsing and storage
"""
import logging
from celery import shared_task
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal, set_tenant_schema
from app.models.document import DocumentType
from app.parsers.detector import Detector
from app.parsers.sped_efd_icms import SPEDParser, ParseError as SPEDParseError
from app.parsers.nfe_xml import NFEParser, ParseError as NFEParseError
from app.parsers.cte_xml import CTEParser, ParseError as CTEParseError
from app.parsers.efd_contribuicoes import EFDContribuicoesParser, EFDContribuicoesParseError
from app.services.storage_service import StorageService, StorageServiceError
from app.services.document_service import DocumentService, DocumentServiceError
from app.tasks.validate_document import validate_document

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="parse_document", max_retries=3)
def parse_document(self, document_id: int, tenant_id: str) -> dict:
    """
    Main document parsing task.

    Orchestrates:
    1. Download from MinIO
    2. Detect document type
    3. Parse with appropriate parser
    4. Persist to PostgreSQL (tenant schema)
    5. Update document status

    Args:
        self: Celery task instance
        document_id: Document record ID (from documents table)
        tenant_id: Organization/tenant ID

    Returns:
        Result dict with status and summary

    Raises:
        Task retries on transient errors (MinIO, DB connection)
        Marks as failed on ParseError or fatal errors
    """
    db = None
    try:
        db = SessionLocal()

        # Set tenant schema
        set_tenant_schema(db, tenant_id)

        # Get Document record
        from app.models.document import Document
        doc = db.query(Document).filter_by(id=document_id).first()
        if not doc:
            logger.error(f"Document {document_id} not found")
            return {
                "status": "failed",
                "error": f"Document {document_id} not found",
            }

        # Update status to processing
        doc.processing_status = "processing"
        db.commit()

        # Download from MinIO
        logger.info(f"Downloading document {document_id} from MinIO: {doc.storage_key}")
        storage = StorageService()
        content = storage.download(doc.storage_key)
        logger.info(f"Downloaded {len(content)} bytes")

        # Detect document type (unless already known)
        if doc.document_type == DocumentType.UNKNOWN:
            logger.info(f"Detecting document type for {document_id}")
            detected_type = Detector.detect(doc.original_filename, content.decode('utf-8', errors='ignore'))
            doc.document_type = DocumentType[detected_type.type.upper().replace("-", "_")]
            db.commit()

        # Parse based on type
        logger.info(f"Parsing document {document_id} as {doc.document_type}")
        parsed_result = _parse_by_type(content, doc.document_type, tenant_id)

        if not parsed_result:
            raise ValueError("Parsing returned empty result")

        # Persist to database
        logger.info(f"Saving parsed document {document_id} to database")
        _save_parsed_document(db, tenant_id, document_id, doc.document_type, parsed_result)

        # Update status to completed
        DocumentService.update_document_status(db, document_id, "completed")
        db.commit()

        logger.info(f"Successfully processed document {document_id}")

        # Chain validation task on successful parse
        validate_document.delay(document_id, tenant_id, triggered_by="parser")
        logger.info(f"Queued validation task for document {document_id}")

        return {
            "status": "completed",
            "document_id": document_id,
            "document_type": str(doc.document_type),
        }

    except (SPEDParseError, NFEParseError, CTEParseError, EFDContribuicoesParseError) as e:
        # Parsing errors are fatal - don't retry
        logger.error(f"Parse error in document {document_id}: {str(e)}")
        if db:
            try:
                DocumentService.update_document_status(db, document_id, "failed", str(e))
                db.commit()
            except Exception as db_err:
                logger.error(f"Failed to update status: {str(db_err)}")

        return {
            "status": "failed",
            "error": f"Parse error: {str(e)}",
        }

    except StorageServiceError as e:
        # Storage errors are transient - retry
        logger.warning(f"Storage error in document {document_id}: {str(e)}")
        retry_count = self.request.retries
        if retry_count < self.max_retries:
            # Exponential backoff: 60, 120, 240 seconds
            countdown = 60 * (2 ** retry_count)
            logger.info(f"Retrying task in {countdown} seconds (attempt {retry_count + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=countdown)
        else:
            logger.error(f"Max retries exceeded for document {document_id}")
            if db:
                try:
                    DocumentService.update_document_status(db, document_id, "failed", f"Storage error after retries: {str(e)}")
                    db.commit()
                except Exception as db_err:
                    logger.error(f"Failed to update status: {str(db_err)}")
            return {
                "status": "failed",
                "error": f"Storage error after {self.max_retries} retries: {str(e)}",
            }

    except DocumentServiceError as e:
        # Database errors are transient - retry
        logger.warning(f"Database error in document {document_id}: {str(e)}")
        retry_count = self.request.retries
        if retry_count < self.max_retries:
            countdown = 60 * (2 ** retry_count)
            logger.info(f"Retrying task in {countdown} seconds (attempt {retry_count + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=countdown)
        else:
            logger.error(f"Max retries exceeded for document {document_id}")
            return {
                "status": "failed",
                "error": f"Database error after {self.max_retries} retries: {str(e)}",
            }

    except Exception as e:
        # Unexpected errors - log and fail
        logger.error(f"Unexpected error processing document {document_id}: {str(e)}", exc_info=True)
        if db:
            try:
                DocumentService.update_document_status(db, document_id, "failed", f"Unexpected error: {str(e)}")
                db.commit()
            except Exception as db_err:
                logger.error(f"Failed to update status: {str(db_err)}")
        return {
            "status": "failed",
            "error": f"Unexpected error: {str(e)}",
        }

    finally:
        if db:
            db.close()


def _parse_by_type(content: bytes, document_type: DocumentType, tenant_id: str) -> dict:
    """
    Parse document based on its type.

    Args:
        content: File content (bytes)
        document_type: Document type enum
        tenant_id: Tenant ID (for parser initialization)

    Returns:
        Parsed result dict

    Raises:
        ParseError: If parsing fails
    """
    content_str = content.decode('utf-8', errors='ignore')

    if document_type == DocumentType.SPED_EFD_ICMS:
        parser = SPEDParser(tenant_id)
        return parser.parse(content_str)

    elif document_type == DocumentType.NFE:
        parser = NFEParser(tenant_id)
        return parser.parse(content_str)

    elif document_type == DocumentType.CTE:
        parser = CTEParser(tenant_id)
        return parser.parse(content_str)

    elif document_type == DocumentType.EFD_CONTRIBUICOES:
        parser = EFDContribuicoesParser(tenant_id)
        return parser.parse_bytes(content)

    else:
        raise ValueError(f"Unsupported document type: {document_type}")


def _save_parsed_document(
    db: Session,
    tenant_id: str,
    document_id: int,
    document_type: DocumentType,
    parsed_result: dict,
) -> None:
    """
    Save parsed document to database.

    Args:
        db: SQLAlchemy session
        tenant_id: Tenant ID
        document_id: Document record ID
        document_type: Document type
        parsed_result: Parsed data dict

    Raises:
        DocumentServiceError: If save fails
    """
    if document_type == DocumentType.SPED_EFD_ICMS:
        DocumentService.save_fiscal_document_from_sped(db, tenant_id, document_id, parsed_result)

    elif document_type == DocumentType.NFE:
        DocumentService.save_fiscal_document_from_nfe(db, tenant_id, document_id, parsed_result)

    elif document_type == DocumentType.CTE:
        DocumentService.save_ct_document_from_cte(db, tenant_id, document_id, parsed_result)

    elif document_type == DocumentType.EFD_CONTRIBUICOES:
        DocumentService.save_efd_contribuicoes(db, tenant_id, document_id, parsed_result)

    else:
        raise DocumentServiceError(f"Unsupported document type for saving: {document_type}")
