"""
Celery task for document validation using the rule engine
"""
import logging
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal, set_tenant_schema
from app.models.document import Document
from app.models.fiscal_document import FiscalDocument
from app.models.ct_document import CTDocument
from app.models.rule_log import SeverityLevel
from app.validators.rules.dag import RuleDAG
from app.validators.rules.registry import get_active_rules
import app.validators.rules.fiscal_rules  # noqa: F401 — registra as regras no registry
import app.validators.rules.anomaly_rules  # noqa: F401 — registra regras de anomalia
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

        # Load parent Document once (for document_type injection into config)
        parent_doc = db.query(Document).filter_by(id=document_id).first()
        source_type = parent_doc.document_type.value if parent_doc else None

        # Load CT-e records linked to this document (for CteCanceladoRule)
        ct_docs = (
            db.query(CTDocument)
            .filter_by(document_id=document_id, superseded=False)
            .all()
        )

        # Pre-fetch historical valor_total per emitente_cnpj (for ValorAnomalyRule Z-score)
        # One query per unique CNPJ — avoids N+1 inside the rule execution
        emitente_cnpjs = {fd.emitente_cnpj for fd in fiscal_docs if fd.emitente_cnpj}
        current_ids = [fd.id for fd in fiscal_docs]
        supplier_valor_history: dict[str, list[float]] = {}
        for cnpj in emitente_cnpjs:
            rows = (
                db.query(FiscalDocument.valor_total)
                .filter(
                    FiscalDocument.tenant_id == tenant_id,
                    FiscalDocument.emitente_cnpj == cnpj,
                    FiscalDocument.superseded == False,
                    FiscalDocument.id.notin_(current_ids),
                )
                .limit(200)
                .all()
            )
            supplier_valor_history[cnpj] = [float(r[0]) for r in rows if r[0] is not None]

        # Execute rules against each FiscalDocument
        from datetime import date as _date
        for fdoc in fiscal_docs:
            logger.info(f"Running rules on fiscal_document {fdoc.id} ({fdoc.chave_acesso})")

            config = RuleService.get_config(db, tenant_id, "*")
            # Inject per-document context so rules can adapt their behavior
            config["source_document_type"] = source_type
            config["ct_documents"] = ct_docs
            config["supplier_valor_history"] = supplier_valor_history
            config["validation_date"] = _date.today()

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

        # Fire critical alert email (non-blocking — failure doesn't affect task result)
        if critical_results:
            try:
                from app.services.email_service import send_critical_alert_email
                from app.services.scoring_service import ScoringService
                alerts_payload = []
                for r in critical_results:
                    # Find the fiscal_doc that produced this result to estimate exposure
                    fdoc_match = next(
                        (fd for fd in fiscal_docs if any(rl.id == r.id for rl in fd.rule_logs)),
                        fiscal_docs[0],
                    )
                    _, exposure = ScoringService.calculate_alert_severity(r, fdoc_match)
                    alerts_payload.append({
                        "rule_id": r.rule_id,
                        "message": r.message,
                        "exposure": float(exposure),
                    })
                send_critical_alert_email(
                    tenant_id=tenant_id,
                    document_id=document_id,
                    original_filename=parent_doc.original_filename if parent_doc else f"doc_{document_id}",
                    critical_alerts=alerts_payload,
                )
            except Exception as email_exc:
                logger.warning("Email alert dispatch failed (non-fatal): %s", email_exc)

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
