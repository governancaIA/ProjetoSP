"""
Celery task for document validation using the rule engine
"""
import logging
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal, set_tenant_schema
from app.models.document import Document
from app.models.fiscal_document import FiscalDocument
from app.models.rule_log import SeverityLevel
from app.validators.rules.dag import RuleDAG
from app.validators.rules.registry import get_active_rules
from app.services.rule_service import RuleService, RuleServiceError


logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="validate_document", max_retries=3)
def validate_document(
    self,
    document_id: int,
    tenant_id: str,
    triggered_by: str = "parser",
) -> dict:
    """
    Main document validation task.

    Orchestrates:
    1. Load FiscalDocument(s) for a Document
    2. Execute DAG of rules against each document
    3. Persist RuleExecutionLog for each result
    4. Update Document status

    Args:
        self: Celery task instance
        document_id: Document record ID
        tenant_id: Organization/tenant ID
        triggered_by: Source of validation ("parser", "reprocess", "manual_validation")

    Returns:
        Result dict with status and summary

    Raises:
        Task retries on transient errors (DB connection)
        Marks as failed on fatal errors
    """
    db = None
    try:
        db = SessionLocal()
        set_tenant_schema(db, tenant_id)

        # Get all non-superseded FiscalDocuments for this Document
        fiscal_docs = db.query(FiscalDocument).filter_by(
            document_id=document_id,
            superseded=False,
        ).all()

        if not fiscal_docs:
            logger.warning(f"No fiscal documents found for document {document_id}")
            return {
                "status": "failed",
                "error": f"No fiscal documents found for document {document_id}",
            }

        logger.info(f"Validating {len(fiscal_docs)} fiscal document(s) for document {document_id}")

        # Initialize the rule DAG
        rules = get_active_rules()
        if not rules:
            logger.warning("No rules registered in rule engine")
            return {
                "status": "completed",
                "document_id": document_id,
                "total_rules": 0,
                "passed": 0,
                "failed": 0,
                "critical": 0,
            }

        dag = RuleDAG(rules)
        all_results = []

        # Execute rules against each FiscalDocument
        for fdoc in fiscal_docs:
            logger.info(f"Running rules on fiscal_document {fdoc.id} ({fdoc.chave_acesso})")

            # Get tenant-specific config
            config = RuleService.get_config(db, tenant_id, "*")

            # Execute all rules for this document
            results = dag.execute(fdoc, fdoc.items, config)

            # Persist results
            RuleService.save_results(db, tenant_id, fdoc.id, results, triggered_by)
            all_results.extend(results)

        # Commit all results
        db.commit()
        logger.info(f"Validation complete: {len(all_results)} rule results persisted")

        # Summarize results
        failed_results = [r for r in all_results if not r.passed]
        critical_results = [r for r in failed_results if r.severity == SeverityLevel.CRITICAL]

        return {
            "status": "completed",
            "document_id": document_id,
            "total_rules": len(all_results),
            "passed": len(all_results) - len(failed_results),
            "failed": len(failed_results),
            "critical": len(critical_results),
        }

    except RuleServiceError as e:
        # Database error - retry with exponential backoff
        logger.warning(f"Rule service error in document {document_id}: {str(e)}")
        retry_count = self.request.retries
        if retry_count < self.max_retries:
            countdown = 60 * (2 ** retry_count)
            logger.info(f"Retrying task in {countdown} seconds (attempt {retry_count + 1}/{self.max_retries})")
            raise self.retry(exc=e, countdown=countdown)
        else:
            logger.error(f"Max retries exceeded for document {document_id}")
            return {
                "status": "failed",
                "error": f"Rule service error after {self.max_retries} retries: {str(e)}",
            }

    except Exception as e:
        # Unexpected error - log and fail
        logger.error(f"Unexpected error validating document {document_id}: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "error": f"Unexpected error: {str(e)}",
        }

    finally:
        if db:
            db.close()
