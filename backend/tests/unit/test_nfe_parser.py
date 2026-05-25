"""
Tests for NF-e XML Parser (US-1.6)
"""
import pytest
from app.parsers.nfe_xml import NFEParser, ParseError


@pytest.fixture
def minimal_nfe():
    """Minimal valid NF-e XML for unit testing"""
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


@pytest.fixture
def nfe_canceled():
    """NF-e marked as canceled (cStat = 101)"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
  <NFe>
    <infNFe Id="NFe35180166047275000199550010000000011234567890" versao="4.00">
      <ide>
        <cUF>35</cUF>
        <nNF>000000002</nNF>
        <serie>001</serie>
        <tpNF>0</tpNF>
        <dhEmi>2018-01-02T10:00:00-03:00</dhEmi>
        <dhSaiEnt>2018-01-02T10:00:00-03:00</dhSaiEnt>
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
          <cProd>002</cProd>
          <xProd>PRODUTO TESTE 2</xProd>
          <NCM>87654321</NCM>
          <CFOP>1101</CFOP>
          <uCom>UN</uCom>
          <qCom>2.0000</qCom>
          <vUnCom>50.00</vUnCom>
          <vProd>100.00</vProd>
          <vDesc>0.00</vDesc>
        </prod>
        <imposto>
          <ICMS><ICMS10><CST>10</CST><vBC>100.00</vBC><pICMS>12.00</pICMS><vICMS>12.00</vICMS></ICMS10></ICMS>
          <PIS><PISAliq><vBC>0.00</vBC><pPIS>0.00</pPIS><vPIS>0.00</vPIS></PISAliq></PIS>
          <COFINS><COFINSAliq><vBC>0.00</vBC><pCOFINS>0.00</pCOFINS><vCOFINS>0.00</vCOFINS></COFINSAliq></COFINS>
        </imposto>
      </det>
      <total>
        <ICMSTot>
          <vNF>100.00</vNF>
          <vICMS>12.00</vICMS>
          <vPIS>0.00</vPIS>
          <vCOFINS>0.00</vCOFINS>
          <vIPI>0.00</vIPI>
        </ICMSTot>
      </total>
    </infNFe>
  </NFe>
  <protNFe>
    <infProt>
      <cStat>101</cStat>
      <xMotivo>Cancelamento de NF-e homologada ou de autorização de NF-e</xMotivo>
      <nProt>135180000000002</nProt>
      <dhRecbto>2018-01-02T10:05:00-03:00</dhRecbto>
    </infProt>
  </protNFe>
</nfeProc>"""


def test_parser_initialization():
    """Test parser can be instantiated with tenant_id"""
    parser = NFEParser(tenant_id="org_001")
    assert parser.tenant_id == "org_001"


def test_parse_minimal_nfe(minimal_nfe):
    """Test parsing a minimal valid NF-e"""
    parser = NFEParser(tenant_id="org_001")
    result = parser.parse(minimal_nfe)

    assert "nfe" in result
    assert "itens" in result
    assert "metadata" in result
    assert len(result["itens"]) == 1
    assert result["nfe"]["status"] == "autorizado"
    assert result["nfe"]["cancelado"] is False


def test_parse_nfe_header(minimal_nfe):
    """Test NF-e header extraction"""
    parser = NFEParser(tenant_id="org_001")
    result = parser.parse(minimal_nfe)

    nfe = result["nfe"]
    assert nfe["chave_acesso"] == "35180166047275000199550010000000011234567890"
    assert nfe["numero_nf"] == "000000001"
    assert nfe["serie"] == "001"
    assert nfe["natureza"] == "saída"
    assert nfe["emitente_cnpj"] == "66047275000199"
    assert nfe["emitente_nome"] == "EMPRESA TESTE LTDA"
    assert nfe["destinatario_cnpj"] == "12345678000195"
    assert nfe["destinatario_nome"] == "DESTINATARIO TESTE LTDA"
    assert nfe["data_emissao"] == "2018-01-01"


def test_parse_nfe_item(minimal_nfe):
    """Test NF-e item extraction with taxes"""
    parser = NFEParser(tenant_id="org_001")
    result = parser.parse(minimal_nfe)

    item = result["itens"][0]
    assert item["item_seq"] == 1
    assert item["codigo_produto"] == "001"
    assert item["descricao"] == "PRODUTO TESTE"
    assert item["ncm"] == "12345678"
    assert item["cfop"] == "5101"
    assert item["cst"] == "00"
    assert item["quantidade"] == 1.0
    assert item["unidade"] == "UN"
    assert item["valor_unitario"] == 100.00
    assert item["valor_item"] == 100.00
    assert item["base_icms"] == 100.00
    assert item["aliquota_icms"] == 12.00
    assert item["valor_icms"] == 12.00
    assert item["base_pis"] == 100.00
    assert item["aliquota_pis"] == 0.65
    assert item["valor_pis"] == 0.65
    assert item["base_cofins"] == 100.00
    assert item["aliquota_cofins"] == 3.00
    assert item["valor_cofins"] == 3.00
    assert item["valor_ipi"] == 0.0


def test_parse_nfe_totals(minimal_nfe):
    """Test NF-e totals extraction"""
    parser = NFEParser(tenant_id="org_001")
    result = parser.parse(minimal_nfe)

    nfe = result["nfe"]
    assert nfe["valor_total"] == 100.00
    assert nfe["valor_icms"] == 12.00
    assert nfe["valor_pis"] == 0.65
    assert nfe["valor_cofins"] == 3.00
    assert nfe["valor_ipi"] == 0.0


def test_parse_nfe_protocolo(minimal_nfe):
    """Test NF-e protocol and authorization info"""
    parser = NFEParser(tenant_id="org_001")
    result = parser.parse(minimal_nfe)

    nfe = result["nfe"]
    assert nfe["protocolo"] == "135180000000001"
    assert nfe["data_autorizacao"] == "2018-01-01"
    assert nfe["status"] == "autorizado"


def test_parse_nfe_cancelado(nfe_canceled):
    """Test detection of canceled NF-e"""
    parser = NFEParser(tenant_id="org_001")
    result = parser.parse(nfe_canceled)

    nfe = result["nfe"]
    assert nfe["status"] == "cancelado"
    assert nfe["cancelado"] is True
    assert result["metadata"]["cancelado"] is True


def test_parse_nfe_entrada(nfe_canceled):
    """Test parsing entrada (tpNF=0) vs saída (tpNF=1)"""
    parser = NFEParser(tenant_id="org_001")
    result = parser.parse(nfe_canceled)

    nfe = result["nfe"]
    assert nfe["natureza"] == "entrada"


def test_parse_invalid_nfe():
    """Test parsing invalid NF-e raises ParseError"""
    parser = NFEParser(tenant_id="org_001")

    with pytest.raises(ParseError):
        parser.parse("")

    with pytest.raises(ParseError):
        parser.parse("not xml")

    with pytest.raises(ParseError):
        parser.parse("<?xml version='1.0'?><root/>")


def test_metadata_generation(minimal_nfe):
    """Test metadata is correctly generated"""
    parser = NFEParser(tenant_id="org_001")
    result = parser.parse(minimal_nfe)

    metadata = result["metadata"]
    assert metadata["tenant_id"] == "org_001"
    assert metadata["total_itens"] == 1
    assert metadata["cancelado"] is False
    assert "parsed_at" in metadata
    assert "warnings" in metadata
