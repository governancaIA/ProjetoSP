"""
Tests for CT-e XML Parser (US-1.7)
"""
import pytest
from app.parsers.cte_xml import CTEParser, ParseError


@pytest.fixture
def minimal_cte():
    """Minimal valid CT-e XML for unit testing"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
  <CTe>
    <infCte Id="CTe35180166047275000199570010000000011234567890" versao="3.00">
      <ide>
        <cUF>35</cUF>
        <nCT>000000001</nCT>
        <serie>001</serie>
        <dhEmi>2018-01-01T10:00:00-03:00</dhEmi>
        <natOp>Normal</natOp>
      </ide>
      <emit>
        <CNPJ>66047275000199</CNPJ>
        <xNome>TRANSPORTADORA TESTE LTDA</xNome>
      </emit>
      <rem>
        <CNPJ>99999999000199</CNPJ>
        <xNome>REMETENTE TESTE LTDA</xNome>
      </rem>
      <dest>
        <CNPJ>12345678000195</CNPJ>
        <xNome>DESTINATARIO TESTE LTDA</xNome>
      </dest>
      <vPrest>
        <vTPrest>500.00</vTPrest>
      </vPrest>
      <imp>
        <ICMS>
          <ICMS00>
            <CST>00</CST>
            <vBC>500.00</vBC>
            <pICMS>12.00</pICMS>
            <vICMS>60.00</vICMS>
          </ICMS00>
        </ICMS>
      </imp>
    </infCte>
  </CTe>
  <protCTe>
    <infProt>
      <cStat>100</cStat>
      <xMotivo>Autorizado o uso da CT-e</xMotivo>
      <nProt>135180000000001</nProt>
      <dhRecbto>2018-01-01T10:05:00-03:00</dhRecbto>
    </infProt>
  </protCTe>
</cteProc>"""


@pytest.fixture
def cte_canceled():
    """CT-e marked as canceled (cStat = 101)"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
  <CTe>
    <infCte Id="CTe35180166047275000199570010000000011234567890" versao="3.00">
      <ide>
        <cUF>35</cUF>
        <nCT>000000002</nCT>
        <serie>001</serie>
        <dhEmi>2018-01-02T10:00:00-03:00</dhEmi>
        <natOp>Normal</natOp>
      </ide>
      <emit>
        <CNPJ>66047275000199</CNPJ>
        <xNome>TRANSPORTADORA TESTE LTDA</xNome>
      </emit>
      <rem>
        <CNPJ>99999999000199</CNPJ>
        <xNome>REMETENTE TESTE LTDA</xNome>
      </rem>
      <dest>
        <CNPJ>12345678000195</CNPJ>
        <xNome>DESTINATARIO TESTE LTDA</xNome>
      </dest>
      <vPrest>
        <vTPrest>300.00</vTPrest>
      </vPrest>
      <imp>
        <ICMS>
          <ICMS10>
            <vICMS>36.00</vICMS>
          </ICMS10>
        </ICMS>
      </imp>
    </infCte>
  </CTe>
  <protCTe>
    <infProt>
      <cStat>101</cStat>
      <xMotivo>Cancelamento de CT-e</xMotivo>
      <nProt>135180000000002</nProt>
      <dhRecbto>2018-01-02T10:05:00-03:00</dhRecbto>
    </infProt>
  </protCTe>
</cteProc>"""


def test_parser_initialization():
    """Test parser can be instantiated with tenant_id"""
    parser = CTEParser(tenant_id="org_001")
    assert parser.tenant_id == "org_001"


def test_parse_minimal_cte(minimal_cte):
    """Test parsing a minimal valid CT-e"""
    parser = CTEParser(tenant_id="org_001")
    result = parser.parse(minimal_cte)

    assert "cte" in result
    assert "metadata" in result
    assert result["cte"]["status"] == "autorizado"
    assert result["cte"]["cancelado"] is False


def test_parse_cte_header(minimal_cte):
    """Test CT-e header extraction"""
    parser = CTEParser(tenant_id="org_001")
    result = parser.parse(minimal_cte)

    cte = result["cte"]
    assert cte["chave_acesso"] == "35180166047275000199570010000000011234567890"
    assert cte["numero_cte"] == "000000001"
    assert cte["serie"] == "001"
    assert cte["transportador_cnpj"] == "66047275000199"
    assert cte["transportador_nome"] == "TRANSPORTADORA TESTE LTDA"
    assert cte["remetente_cnpj"] == "99999999000199"
    assert cte["destinatario_cnpj"] == "12345678000195"
    assert cte["data_emissao"] == "2018-01-01"


def test_parse_cte_transport(minimal_cte):
    """Test CT-e transport details"""
    parser = CTEParser(tenant_id="org_001")
    result = parser.parse(minimal_cte)

    cte = result["cte"]
    assert cte["natureza_operacao"] == "Normal"
    assert cte["valor_total"] == 500.00
    assert cte["valor_icms"] == 60.00


def test_parse_cte_protocolo(minimal_cte):
    """Test CT-e protocol and authorization info"""
    parser = CTEParser(tenant_id="org_001")
    result = parser.parse(minimal_cte)

    cte = result["cte"]
    assert cte["protocolo"] == "135180000000001"
    assert cte["data_autorizacao"] == "2018-01-01"
    assert cte["status"] == "autorizado"


def test_parse_cte_cancelado(cte_canceled):
    """Test detection of canceled CT-e"""
    parser = CTEParser(tenant_id="org_001")
    result = parser.parse(cte_canceled)

    cte = result["cte"]
    assert cte["status"] == "cancelado"
    assert cte["cancelado"] is True
    assert result["metadata"]["cancelado"] is True


def test_parse_invalid_cte():
    """Test parsing invalid CT-e raises ParseError"""
    parser = CTEParser(tenant_id="org_001")

    with pytest.raises(ParseError):
        parser.parse("")

    with pytest.raises(ParseError):
        parser.parse("not xml")

    with pytest.raises(ParseError):
        parser.parse("<?xml version='1.0'?><root/>")


def test_metadata_generation(minimal_cte):
    """Test metadata is correctly generated"""
    parser = CTEParser(tenant_id="org_001")
    result = parser.parse(minimal_cte)

    metadata = result["metadata"]
    assert metadata["tenant_id"] == "org_001"
    assert metadata["cancelado"] is False
    assert "parsed_at" in metadata
    assert "warnings" in metadata
