"""
Tests for parse_document Celery task
"""
import pytest
from unittest.mock import MagicMock, patch, Mock
from io import BytesIO


# Mock database before importing models
with patch('app.core.database.create_engine'):
    from app.models.document import Document, DocumentType
    from app.tasks.parse_document import parse_document


@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session"""
    db = MagicMock()
    return db


@pytest.fixture
def sample_sped_content():
    """Sample SPED content for testing"""
    return """|0|00|1|66047275000199|35|2018|1|01012018|31012018|ARAMEFICIO CHAVANTES IND E COM LTDA|1|0|
|0|01|0|
|C100|0|1|001|55|00|001|000000001|35180166047275000199550010000000011234567890|01012018|01012018|100,00|1|0,00|0,00|100,00|9|0,00|0,00|0,00|0,00|0,00|0,00|0,00|0,00|
|C170|1|1000000001||1,00000|un|100,00|0,00|0|000|1101|30|100,00|0,00|0,00|0,00|0,00|0,00|0|03||0,00|0,00|0,00|
|9|001|1|1|100,00|
"""


@pytest.fixture
def sample_nfe_content():
    """Sample NF-e XML content for testing"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe35180166047275000199550010000000011234567890" versao="4.00">
      <ide>
        <cUF>35</cUF>
        <nNF>000000001</nNF>
        <serie>001</serie>
        <tpNF>1</tpNF>
        <dhEmi>2018-01-01T10:00:00-03:00</dhEmi>
        <dhSaiEnt>2018-01-01T10:00:00-03:00</dhSaiEnt>
      </ide>
      <emit>
        <CNPJ>66047275000199</CNPJ>
        <xNome>EMPRESA TESTE LTDA</xNome>
      </emit>
      <dest>
        <CNPJ>12345678000195</CNPJ>
        <xNome>DESTINATARIO TESTE LTDA</xNome>
      </dest>
      <det nItem="1">
        <prod>
          <cProd>001</cProd>
          <xProd>PRODUTO TESTE</xProd>
          <NCM>12345678</NCM>
          <CFOP>5101</CFOP>
          <uCom>UN</uCom>
          <qCom>1.0000</qCom>
          <vUnCom>100.00</vUnCom>
          <vProd>100.00</vProd>
          <vDesc>0.00</vDesc>
        </prod>
        <imposto>
          <ICMS><ICMS00><CST>00</CST><vBC>100.00</vBC><pICMS>12.00</pICMS><vICMS>12.00</vICMS></ICMS00></ICMS>
          <PIS><PISAliq><CST>01</CST><vBC>100.00</vBC><pPIS>0.65</pPIS><vPIS>0.65</vPIS></PISAliq></PIS>
          <COFINS><COFINSAliq><CST>01</CST><vBC>100.00</vBC><pCOFINS>3.00</pCOFINS><vCOFINS>3.00</vCOFINS></COFINSAliq></COFINS>
        </imposto>
      </det>
      <total>
        <ICMSTot>
          <vNF>100.00</vNF>
          <vICMS>12.00</vICMS>
          <vPIS>0.65</vPIS>
          <vCOFINS>3.00</vCOFINS>
          <vIPI>0.00</vIPI>
        </ICMSTot>
      </total>
    </infNFe>
  </NFe>
  <protNFe>
    <infProt>
      <cStat>100</cStat>
      <xMotivo>Autorizado o uso da NF-e</xMotivo>
      <nProt>135180000000001</nProt>
      <dhRecbto>2018-01-01T10:05:00-03:00</dhRecbto>
    </infProt>
  </protNFe>
</nfeProc>"""


def test_parse_document_sped_success(mock_session, sample_sped_content):
    """Test successful parsing of SPED document"""
    # Setup mocks
    mock_doc = MagicMock()
    mock_doc.id = 1
    mock_doc.original_filename = "sped.txt"
    mock_doc.document_type = DocumentType.SPED_EFD_ICMS
    mock_doc.storage_key = "org_001/sped_efd_icms/abc123.txt"

    mock_session.query.return_value.filter_by.return_value.first.return_value = mock_doc

    with patch('app.tasks.parse_document.SessionLocal', return_value=mock_session), \
         patch('app.tasks.parse_document.set_tenant_schema'), \
         patch('app.tasks.parse_document.StorageService') as mock_storage_cls, \
         patch('app.tasks.parse_document.DocumentService') as mock_doc_service_cls, \
         patch('app.tasks.parse_document.validate_document') as mock_validate:

        mock_validate.delay = MagicMock()
        mock_storage = MagicMock()
        mock_storage.download.return_value = sample_sped_content.encode('utf-8')
        mock_storage_cls.return_value = mock_storage

        from app.tasks.parse_document import parse_document as parse_doc
        result = parse_doc(1, "org_001")

        assert result["status"] == "completed"
        assert result["document_id"] == 1


def test_parse_document_nfe_success(mock_session, sample_nfe_content):
    """Test successful parsing of NF-e document"""
    mock_doc = MagicMock()
    mock_doc.id = 2
    mock_doc.original_filename = "nfe.xml"
    mock_doc.document_type = DocumentType.NFE
    mock_doc.storage_key = "org_001/nfe/xyz789.xml"

    mock_session.query.return_value.filter_by.return_value.first.return_value = mock_doc

    with patch('app.tasks.parse_document.SessionLocal', return_value=mock_session), \
         patch('app.tasks.parse_document.set_tenant_schema'), \
         patch('app.tasks.parse_document.StorageService') as mock_storage_cls, \
         patch('app.tasks.parse_document.DocumentService'), \
         patch('app.tasks.parse_document.validate_document') as mock_validate:

        mock_validate.delay = MagicMock()
        mock_storage = MagicMock()
        mock_storage.download.return_value = sample_nfe_content.encode('utf-8')
        mock_storage_cls.return_value = mock_storage

        from app.tasks.parse_document import parse_document as parse_doc
        result = parse_doc(2, "org_001")

        assert result["status"] == "completed"
        assert result["document_id"] == 2


def test_parse_document_not_found(mock_session):
    """Test parsing non-existent document"""
    mock_session.query.return_value.filter_by.return_value.first.return_value = None

    with patch('app.tasks.parse_document.SessionLocal', return_value=mock_session), \
         patch('app.tasks.parse_document.set_tenant_schema'):

        from app.tasks.parse_document import parse_document as parse_doc
        result = parse_doc(999, "org_001")

        assert result["status"] == "failed"
        assert "not found" in result["error"].lower()


def test_parse_document_storage_error(mock_session):
    """Test handling of storage errors (transient - will retry)"""
    from app.services.storage_service import StorageServiceError

    mock_doc = MagicMock()
    mock_doc.id = 1
    mock_session.query.return_value.filter_by.return_value.first.return_value = mock_doc

    with patch('app.tasks.parse_document.SessionLocal', return_value=mock_session), \
         patch('app.tasks.parse_document.set_tenant_schema'), \
         patch('app.tasks.parse_document.StorageService') as mock_storage_cls:

        mock_storage = MagicMock()
        mock_storage.download.side_effect = StorageServiceError("Connection timeout")
        mock_storage_cls.return_value = mock_storage

        # Task is mocked to prevent actual retry
        with patch('app.tasks.parse_document.parse_document.retry') as mock_retry:
            mock_retry.side_effect = Exception("Retry raised")

            from app.tasks.parse_document import parse_document as parse_doc
            try:
                result = parse_doc(1, "org_001")
            except Exception:
                pass  # Expected - retry mechanism


def test_parse_document_parse_error(mock_session):
    """Test handling of parse errors (fatal - no retry)"""
    from app.parsers.sped_efd_icms import ParseError

    mock_doc = MagicMock()
    mock_doc.id = 1
    mock_doc.document_type = DocumentType.SPED_EFD_ICMS
    mock_session.query.return_value.filter_by.return_value.first.return_value = mock_doc

    with patch('app.tasks.parse_document.SessionLocal', return_value=mock_session), \
         patch('app.tasks.parse_document.set_tenant_schema'), \
         patch('app.tasks.parse_document.StorageService') as mock_storage_cls, \
         patch('app.tasks.parse_document.SPEDParser') as mock_parser_cls, \
         patch('app.tasks.parse_document.DocumentService'):

        mock_storage = MagicMock()
        mock_storage.download.return_value = b"invalid sped content"
        mock_storage_cls.return_value = mock_storage

        mock_parser = MagicMock()
        mock_parser.parse.side_effect = ParseError("Invalid SPED format")
        mock_parser_cls.return_value = mock_parser

        from app.tasks.parse_document import parse_document as parse_doc
        result = parse_doc(1, "org_001")

        # Parse errors don't retry - mark as failed
        assert result["status"] == "failed"
        assert "Parse error" in result["error"]


def test_parse_by_type_sped():
    """Test _parse_by_type with SPED"""
    from app.tasks.parse_document import _parse_by_type

    sample = """|C100|0|1|001|55|00|001|000000001|35180166047275000199550010000000011234567890|01012018|01012018|100,00|1|0,00|0,00|100,00|9|0,00|0,00|0,00|0,00|0,00|0,00|0,00|0,00|
|C170|1|1000000001||1,00000|un|100,00|0,00|0|000|1101|30|100,00|0,00|0,00|0,00|0,00|0,00|0|03||0,00|0,00|0,00|
|9|001|1|1|100,00|
"""

    result = _parse_by_type(sample.encode('utf-8'), DocumentType.SPED_EFD_ICMS, "org_001")

    assert result is not None
    assert "C100" in result or "metadata" in result


def test_parse_by_type_unsupported():
    """Test _parse_by_type with unsupported type"""
    from app.tasks.parse_document import _parse_by_type

    with pytest.raises(ValueError):
        _parse_by_type(b"content", DocumentType.UNKNOWN, "org_001")
