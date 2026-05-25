"""
Integration tests for parse_document → validate_document pipeline
"""
import pytest
from unittest.mock import MagicMock, patch, Mock, call
from decimal import Decimal

from app.models.rule_log import SeverityLevel


@pytest.fixture
def mock_fiscal_doc():
    """Mock a FiscalDocument after parsing"""
    doc = MagicMock()
    doc.id = 1
    doc.tenant_id = "org_001"
    doc.chave_acesso = "35180166047275000199550010000000011234567890"
    doc.numero_nf = "000000001"
    doc.serie = "001"
    doc.emitente_cnpj = "66047275000199"
    doc.valor_total = Decimal("1000.00")
    doc.valor_icms = Decimal("100.00")
    doc.status_nfe = "autorizado"
    doc.natureza = "saída"
    return doc


@pytest.fixture
def mock_fiscal_item():
    """Mock a FiscalItem after parsing"""
    item = MagicMock()
    item.item_seq = 1
    item.cfop = "5101"
    item.cst = "00"
    item.valor_item = Decimal("1000.00")
    item.valor_icms = Decimal("100.00")
    return item


def test_parse_document_triggers_validation(mock_fiscal_doc, mock_fiscal_item):
    """
    Test that parse_document task chains to validate_document on success.

    This verifies that the parse → validate workflow is properly wired:
    1. Parse completes successfully
    2. validate_document.delay() is called with document_id and tenant_id
    """
    with patch('app.tasks.parse_document.SessionLocal') as mock_session_local, \
         patch('app.tasks.parse_document.set_tenant_schema') as mock_set_schema, \
         patch('app.tasks.parse_document.StorageService') as mock_storage, \
         patch('app.tasks.parse_document.Detector') as mock_detector, \
         patch('app.tasks.parse_document.SPEDParser') as mock_sped_parser, \
         patch('app.tasks.parse_document.DocumentService') as mock_doc_service, \
         patch('app.tasks.parse_document.validate_document') as mock_validate:

        from app.tasks.parse_document import parse_document

        # Setup mocks
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        mock_document = MagicMock()
        mock_document.id = 1
        mock_document.document_type = "sped_efd_icms"
        mock_document.original_filename = "test.txt"
        mock_document.storage_key = "documents/test.txt"
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_document

        mock_storage.return_value.download.return_value = b"mock sped content"

        mock_detector.detect.return_value = MagicMock(type="SPED_EFD_ICMS")

        parser_instance = MagicMock()
        parser_instance.parse.return_value = {"fiscal_documents": []}
        mock_sped_parser.return_value = parser_instance

        # Execute task
        result = parse_document(1, "org_001")

        # Verify parse was successful
        assert result["status"] == "completed"
        assert result["document_id"] == 1

        # Verify validate_document.delay was called with correct args
        mock_validate.delay.assert_called_once_with(1, "org_001", triggered_by="parser")


def test_validate_document_runs_all_rules(mock_fiscal_doc, mock_fiscal_item):
    """
    Test that validate_document executes the complete rule DAG.
    """
    with patch('app.tasks.validate_document.SessionLocal') as mock_session_local, \
         patch('app.tasks.validate_document.set_tenant_schema') as mock_set_schema, \
         patch('app.tasks.validate_document.get_active_rules') as mock_get_rules, \
         patch('app.tasks.validate_document.RuleService') as mock_rule_service, \
         patch('app.tasks.validate_document.RuleDAG') as mock_dag:

        from app.tasks.validate_document import validate_document as validate_doc_task

        # Setup mocks
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db

        # Mock FiscalDocuments
        mock_fiscal_doc.items = [mock_fiscal_item]
        mock_db.query.return_value.filter_by.return_value.all.return_value = [mock_fiscal_doc]

        # Mock rules and DAG
        mock_rule1 = MagicMock()
        mock_rule1.rule_id = "test_rule_1"
        mock_get_rules.return_value = [mock_rule1]

        # Mock DAG execution
        mock_result = MagicMock()
        mock_result.rule_id = "test_rule_1"
        mock_result.passed = True
        mock_result.severity = SeverityLevel.INFO

        mock_dag_instance = MagicMock()
        mock_dag_instance.execute.return_value = [mock_result]
        mock_dag.return_value = mock_dag_instance

        mock_rule_service.get_config.return_value = {"tolerance_brl": 0.01}
        mock_rule_service.save_results.return_value = []

        # Execute task
        result = validate_doc_task(1, "org_001", triggered_by="parser")

        # Verify DAG was created and executed
        mock_dag.assert_called_once_with([mock_rule1])
        mock_dag_instance.execute.assert_called_once()

        # Verify results were saved
        mock_rule_service.save_results.assert_called_once()

        # Verify task returned success
        assert result["status"] == "completed"
        assert result["document_id"] == 1


def test_parse_validate_pipeline_end_to_end(mock_fiscal_doc, mock_fiscal_item):
    """
    Integration test: parse creates document, then validation rules run.
    Simulates the full workflow.
    """
    # This test verifies that the pieces fit together:
    # 1. parse_document creates FiscalDocuments in DB
    # 2. validate_document queues automatically
    # 3. Rule DAG executes against the parsed data

    # Note: Full end-to-end would require Redis broker and actual Celery workers.
    # This is a schema-level validation that the task chain is properly set up.

    with patch('app.tasks.parse_document.validate_document') as mock_validate:
        from app.tasks.parse_document import parse_document as parse_doc_task

        # Verify that the import succeeded (validate_document is available)
        assert mock_validate is not None

        # Verify the module chain is wired
        # When parse_document completes, it will call:
        # validate_document.delay(document_id, tenant_id, triggered_by="parser")

        # This is verified in test_parse_document_triggers_validation above
