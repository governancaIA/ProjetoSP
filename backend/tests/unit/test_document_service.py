"""
Tests for DocumentService (persistence layer)
"""
import pytest
from unittest.mock import MagicMock, Mock, patch
from datetime import datetime, date
from decimal import Decimal


# Mock database before importing models
with patch('app.core.database.create_engine'):
    from app.models.document import Document, DocumentType
    from app.models.fiscal_document import FiscalDocument, FiscalItem
    from app.models.ct_document import CTDocument
    from app.services.document_service import DocumentService, DocumentServiceError


@pytest.fixture
def mock_db():
    """Create a mock SQLAlchemy session"""
    db = MagicMock()
    return db


def test_create_document_record_new(mock_db):
    """Test creating a new Document record"""
    # Mock the query result
    mock_db.query.return_value.filter_by.return_value.first.return_value = None

    doc = DocumentService.create_document_record(
        db=mock_db,
        tenant_id="org_001",
        original_filename="sped_jan2018.txt",
        document_type=DocumentType.SPED_EFD_ICMS,
        file_hash="abc123def456",
        file_size=5000,
        storage_key="org_001/sped_efd_icms/abc123def456.txt",
        storage_bucket="fiscalai-documents",
    )

    assert doc is not None
    assert doc.tenant_id == "org_001"
    assert doc.original_filename == "sped_jan2018.txt"
    assert doc.document_version == 1
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()


def test_create_document_record_reprocessamento(mock_db):
    """Test creating a Document record for reprocessamento (same file_hash)"""
    # Mock existing document
    existing_doc = MagicMock()
    existing_doc.document_version = 1
    mock_db.query.return_value.filter_by.return_value.first.return_value = existing_doc

    doc = DocumentService.create_document_record(
        db=mock_db,
        tenant_id="org_001",
        original_filename="sped_jan2018.txt",
        document_type=DocumentType.SPED_EFD_ICMS,
        file_hash="abc123def456",  # Same as existing
        file_size=5000,
        storage_key="org_001/sped_efd_icms/abc123def456.txt",
        storage_bucket="fiscalai-documents",
    )

    # Existing should be marked as superseded
    assert existing_doc.superseded is True
    assert existing_doc.document_version == 2

    # New document should have version 2
    assert doc.document_version == 2


def test_save_fiscal_document_from_sped(mock_db):
    """Test saving SPED parser output to database"""
    parsed_sped = {
        "C100": [
            {
                "chave_acesso": "35180166047275000199550010000000011234567890",
                "numero_nf": "000000001",
                "serie": "001",
                "emitente_cnpj": "66047275000199",
                "emitente_nome": "EMPRESA TESTE LTDA",
                "destinatario_cnpj": "12345678000195",
                "destinatario_nome": "CLIENTE TESTE LTDA",
                "data_emissao": "2018-01-01",
                "data_saida": "2018-01-01",
                "natureza": "saída",
                "valor_total": "100.00",
                "valor_icms": "12.00",
                "valor_pis": "0.65",
                "valor_cofins": "3.00",
                "valor_ipi": "0.00",
                "items": [
                    {
                        "codigo_item": "001",
                        "descricao": "PRODUTO TESTE",
                        "cfop": "5101",
                        "cst": "00",
                        "quantidade": "1.0",
                        "unidade": "UN",
                        "valor_unitario": "100.00",
                        "valor_item": "100.00",
                        "valor_desc": "0.00",
                        "valor_bc_icms": "100.00",
                        "aliq_icms": "12.00",
                        "valor_icms": "12.00",
                        "valor_bc_pis": "0.00",
                        "aliq_pis": "0.00",
                        "valor_pis": "0.00",
                        "valor_bc_cofins": "0.00",
                        "aliq_cofins": "0.00",
                        "valor_cofins": "0.00",
                        "valor_ipi": "0.00",
                    }
                ],
            }
        ],
        "C170": [],
    }

    docs = DocumentService.save_fiscal_document_from_sped(
        db=mock_db,
        tenant_id="org_001",
        document_id=1,
        parsed_sped=parsed_sped,
    )

    assert len(docs) == 1
    assert docs[0].chave_acesso == "35180166047275000199550010000000011234567890"
    assert docs[0].numero_nf == "000000001"
    assert docs[0].valor_total == Decimal("100.00")

    # Verify add was called for doc + items
    assert mock_db.add.call_count >= 2  # doc + at least 1 item


def test_save_fiscal_document_from_nfe(mock_db):
    """Test saving NF-e parser output to database"""
    parsed_nfe = {
        "nfe": {
            "chave_acesso": "35180166047275000199550010000000011234567890",
            "numero_nf": "000000001",
            "serie": "001",
            "emitente_cnpj": "66047275000199",
            "emitente_nome": "EMPRESA TESTE LTDA",
            "destinatario_cnpj": "12345678000195",
            "destinatario_nome": "CLIENTE TESTE LTDA",
            "data_emissao": "2018-01-01",
            "data_saida": "2018-01-01",
            "natureza": "saída",
            "valor_total": 100.00,
            "valor_icms": 12.00,
            "valor_pis": 0.65,
            "valor_cofins": 3.00,
            "valor_ipi": 0.00,
            "status": "autorizado",
            "protocolo": "135180000000001",
            "data_autorizacao": "2018-01-01",
        },
        "itens": [
            {
                "item_seq": 1,
                "codigo_produto": "001",
                "descricao": "PRODUTO TESTE",
                "ncm": "12345678",
                "cfop": "5101",
                "cst": "00",
                "quantidade": 1.0,
                "unidade": "UN",
                "valor_unitario": 100.00,
                "valor_item": 100.00,
                "valor_desconto": 0.00,
                "base_icms": 100.00,
                "aliquota_icms": 12.00,
                "valor_icms": 12.00,
                "base_pis": 100.00,
                "aliquota_pis": 0.65,
                "valor_pis": 0.65,
                "base_cofins": 100.00,
                "aliquota_cofins": 3.00,
                "valor_cofins": 3.00,
                "valor_ipi": 0.00,
            }
        ],
    }

    doc = DocumentService.save_fiscal_document_from_nfe(
        db=mock_db,
        tenant_id="org_001",
        document_id=1,
        parsed_nfe=parsed_nfe,
    )

    assert doc.chave_acesso == "35180166047275000199550010000000011234567890"
    assert doc.status_nfe == "autorizado"
    assert doc.valor_total == Decimal("100.00")
    assert doc.protocolo_nfe == "135180000000001"

    # Verify add was called for doc + items
    assert mock_db.add.call_count >= 2


def test_save_ct_document_from_cte(mock_db):
    """Test saving CT-e parser output to database"""
    parsed_cte = {
        "cte": {
            "chave_acesso": "35180166047275000199570010000000011234567890",
            "numero_cte": "000000001",
            "serie": "001",
            "transportador_cnpj": "66047275000199",
            "transportador_nome": "TRANSPORTADORA TESTE LTDA",
            "remetente_cnpj": "99999999000199",
            "destinatario_cnpj": "12345678000195",
            "data_emissao": "2018-01-01",
            "natureza_operacao": "Normal",
            "valor_total": 500.00,
            "valor_icms": 60.00,
            "status": "autorizado",
            "protocolo": "135180000000001",
            "data_autorizacao": "2018-01-01",
        },
    }

    doc = DocumentService.save_ct_document_from_cte(
        db=mock_db,
        tenant_id="org_001",
        document_id=1,
        parsed_cte=parsed_cte,
    )

    assert doc.chave_acesso == "35180166047275000199570010000000011234567890"
    assert doc.numero_cte == "000000001"
    assert doc.valor_total == Decimal("500.00")
    assert doc.status_cte == "autorizado"

    mock_db.add.assert_called()


def test_update_document_status(mock_db):
    """Test updating Document processing status"""
    mock_doc = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_doc

    DocumentService.update_document_status(
        db=mock_db,
        document_id=1,
        status="completed",
    )

    assert mock_doc.processing_status == "completed"
    assert mock_doc.processed_at is not None


def test_update_document_status_failed(mock_db):
    """Test updating Document status to failed with error message"""
    mock_doc = MagicMock()
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_doc

    error_msg = "File format invalid"
    DocumentService.update_document_status(
        db=mock_db,
        document_id=1,
        status="failed",
        error_message=error_msg,
    )

    assert mock_doc.processing_status == "failed"
    assert mock_doc.processing_error == error_msg


def test_update_document_status_not_found(mock_db):
    """Test updating status for non-existent document raises error"""
    mock_db.query.return_value.filter_by.return_value.first.return_value = None

    with pytest.raises(DocumentServiceError):
        DocumentService.update_document_status(
            db=mock_db,
            document_id=999,
            status="completed",
        )


def test_parse_date():
    """Test date string parsing"""
    result = DocumentService._parse_date("2018-01-15")
    assert result == date(2018, 1, 15)


def test_parse_date_invalid():
    """Test invalid date returns None"""
    result = DocumentService._parse_date("invalid-date")
    assert result is None


def test_parse_date_empty():
    """Test empty date string returns None"""
    result = DocumentService._parse_date("")
    assert result is None
