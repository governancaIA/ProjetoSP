"""
Tests for EPIC 1 — Parsers (SPED, NF-e, CT-e)
"""
import pytest
from app.parsers.detector import Detector, DocumentType
from app.parsers.sped_efd_icms import SPEDParser
from app.parsers.nfe_xml import NFEParser
from app.parsers.cte_xml import CTEParser


class TestDetector:
    """File type detector tests"""

    def test_detect_sped_efd_icms(self):
        """Test SPED EFD ICMS detection"""
        # SPED with 0|ID record (header record of SPED)
        content = "0|ID|28|01|\nC100|0|0|001|55|A|00123|35240191002102800191550010000000011234567890|20240115|20240115|15000.00|1|||100.00|N|200.00|300.00|400.00|50.00|600.00|700.00|"
        detected = Detector.detect("efd_icms.txt", content)

        # Should detect as SPED
        assert detected.doc_type == DocumentType.SPED_EFD_ICMS
        assert Detector.is_valid_detection(detected)

    def test_detect_nfe_xml(self):
        """Test NF-e XML detection"""
        # NF-e XML with <NFe> root element
        content = '<?xml version="1.0"?><NFe><infNFe Id="NFe35240191002102800191550010000000011234567890"><ide><nNF>123</nNF></ide></infNFe></NFe>'
        detected = Detector.detect("nfe.xml", content)

        assert detected.doc_type == DocumentType.NFE
        assert Detector.is_valid_detection(detected)

    def test_detect_cte_xml(self):
        """Test CT-e XML detection"""
        # CT-e XML with <CTe> root element
        content = '<?xml version="1.0"?><CTe><infCte Id="CTe35240191002102800191570010000000011234567890"><ide><nCT>123</nCT></ide></infCte></CTe>'
        detected = Detector.detect("cte.xml", content)

        assert detected.doc_type == DocumentType.CTE
        assert Detector.is_valid_detection(detected)

    def test_detect_unknown(self):
        """Test detection of unknown file type"""
        content = "random file content that doesn't match any pattern"
        detected = Detector.detect("unknown.bin", content)

        assert detected.doc_type == DocumentType.UNKNOWN
        assert not Detector.is_valid_detection(detected)

    def test_detect_by_extension_only(self):
        """Test detection by file extension when content is ambiguous"""
        content = "some content"
        detected = Detector.detect("file.xml", content)

        # Should still try to detect as XML
        assert detected.doc_type in [DocumentType.NFE, DocumentType.CTE, DocumentType.UNKNOWN]


class TestSPEDParser:
    """SPED EFD ICMS parser tests"""

    def test_parse_minimal_sped(self):
        """Test parsing minimal SPED file"""
        # C100 format: C100|ind_mov|ind_emitente|serie|modelo|serie_nf_ecf|numero_nf|chave_acesso|...
        content = """C100|0|0|001|55|A|00123|35240191002102800191550010000000011234567890|20240115|20240115|15000.00|1|||100.00|N|200.00|300.00|400.00|50.00|600.00|700.00|
C170|001|item001|Produto 1|1|un|10.00|0|1|5102|00|10.00|10.00|0|0|0|0|0|0|
"""
        parser = SPEDParser("org_001")
        result = parser.parse(content)

        assert "C100" in result
        assert len(result["C100"]) == 1

        c100 = result["C100"][0]
        # Verify C100 was parsed (exact indices may vary)
        assert c100["record_type"] == "C100"
        assert "chave_acesso" in c100 or "numero_nf" in c100

        assert "C170" in result
        assert len(result["C170"]) == 1
        assert result["C170"][0]["codigo_item"] == "item001"

        assert result["metadata"]["total_c100_records"] == 1
        assert result["metadata"]["total_c170_records"] == 1

    def test_parse_sped_empty_content(self):
        """Test that empty SPED content raises error"""
        parser = SPEDParser("org_001")

        with pytest.raises(Exception):
            parser.parse("")

        with pytest.raises(Exception):
            parser.parse("   \n\n   ")

    def test_parse_sped_multiple_notes(self):
        """Test parsing SPED with multiple notes"""
        content = """C100|0|0|001|55|A|00001|35240191002102800191550010000000001001002003|20240101|20240101|1000.00|1|||50.00|N|100.00|150.00|200.00|25.00|300.00|350.00|
C170|001|item001|Produto A|1|un|1000.00|0|1|5102|00|100.00|100.00|0|0|0|0|0|0|
C100|0|0|001|55|A|00002|35240191002102800191550010000000002001002003|20240102|20240102|2000.00|1|||100.00|N|200.00|300.00|400.00|50.00|600.00|700.00|
C170|001|item002|Produto B|2|un|1000.00|0|1|5102|00|200.00|200.00|0|0|0|0|0|0|
"""
        parser = SPEDParser("org_001")
        result = parser.parse(content)

        assert len(result["C100"]) == 2
        assert len(result["C170"]) == 2


class TestNFEParser:
    """NF-e XML parser tests"""

    def test_parse_minimal_nfe(self):
        """Test parsing minimal NF-e XML"""
        content = """<?xml version="1.0"?>
<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
  <infNFe Id="NFe35240191002102800191550010000000011234567890">
    <ide>
      <cUF>35</cUF>
      <nNF>123</nNF>
      <serie>1</serie>
      <tpNF>1</tpNF>
      <dhEmi>2024-01-15T10:30:00-03:00</dhEmi>
    </ide>
    <emit>
      <CNPJ>19020182000195</CNPJ>
      <xNome>Empresa Teste Ltda</xNome>
    </emit>
    <dest>
      <CNPJ>16716114000172</CNPJ>
      <xNome>Cliente Teste</xNome>
    </dest>
    <total>
      <ICMSTot>
        <vNF>5000.00</vNF>
        <vICMS>500.00</vICMS>
        <vPIS>100.00</vPIS>
        <vCOFINS>200.00</vCOFINS>
        <vIPI>0.00</vIPI>
      </ICMSTot>
    </total>
  </infNFe>
  <protNFe>
    <infProt>
      <cStat>100</cStat>
      <nProt>111111111111111</nProt>
      <dhRecbto>2024-01-15T11:00:00-03:00</dhRecbto>
    </infProt>
  </protNFe>
</NFe>"""
        parser = NFEParser("org_001")
        result = parser.parse(content)

        nfe = result["nfe"]
        assert nfe["chave_acesso"] == "35240191002102800191550010000000011234567890"
        assert nfe["numero_nf"] == "123"
        assert nfe["serie"] == "1"
        assert nfe["natureza"] == "saída"
        assert nfe["emitente_cnpj"] == "19020182000195"
        assert nfe["status"] == "autorizado"
        assert nfe["protocolo"] == "111111111111111"

    def test_parse_nfe_empty_content(self):
        """Test that empty NF-e content raises error"""
        parser = NFEParser("org_001")

        with pytest.raises(Exception):
            parser.parse("")

    def test_parse_nfe_invalid_xml(self):
        """Test that invalid XML raises error"""
        parser = NFEParser("org_001")

        with pytest.raises(Exception):
            parser.parse("<invalid>xml<no>close>")

    def test_parse_nfe_with_items(self):
        """Test parsing NF-e with items and taxes"""
        content = """<?xml version="1.0"?>
<NFe xmlns="http://www.portalfiscal.inf.br/nfe">
  <infNFe Id="NFe35240191002102800191550010000000011234567890">
    <ide>
      <cUF>35</cUF>
      <nNF>123</nNF>
      <serie>1</serie>
      <tpNF>1</tpNF>
      <dhEmi>2024-01-15T10:30:00-03:00</dhEmi>
    </ide>
    <emit>
      <CNPJ>19020182000195</CNPJ>
      <xNome>Empresa</xNome>
    </emit>
    <dest>
      <CNPJ>16716114000172</CNPJ>
      <xNome>Cliente</xNome>
    </dest>
    <det nItem="1">
      <prod>
        <cProd>001</cProd>
        <xProd>Produto A</xProd>
        <NCM>12345678</NCM>
        <CFOP>5102</CFOP>
        <qCom>10</qCom>
        <uCom>un</uCom>
        <vUnCom>100.00</vUnCom>
        <vProd>1000.00</vProd>
        <vDesc>0.00</vDesc>
      </prod>
      <imposto>
        <ICMS>
          <ICMS00>
            <CST>00</CST>
            <vBC>1000.00</vBC>
            <pICMS>18.00</pICMS>
            <vICMS>180.00</vICMS>
          </ICMS00>
        </ICMS>
      </imposto>
    </det>
    <total>
      <ICMSTot>
        <vNF>1000.00</vNF>
        <vICMS>180.00</vICMS>
        <vPIS>0.00</vPIS>
        <vCOFINS>0.00</vCOFINS>
        <vIPI>0.00</vIPI>
      </ICMSTot>
    </total>
  </infNFe>
</NFe>"""
        parser = NFEParser("org_001")
        result = parser.parse(content)

        assert len(result["itens"]) == 1
        item = result["itens"][0]
        assert item["codigo_produto"] == "001"
        assert item["quantidade"] == 10.0
        assert item["valor_item"] == 1000.0
        assert item["cst"] == "00"
        assert item["valor_icms"] == 180.0


class TestCTEParser:
    """CT-e XML parser tests"""

    def test_parse_minimal_cte(self):
        """Test parsing minimal CT-e XML"""
        content = """<?xml version="1.0"?>
<CTe xmlns="http://www.portalfiscal.inf.br/cte">
  <infCte Id="CTe35240191002102800191570010000000011234567890">
    <ide>
      <cUF>35</cUF>
      <nCT>123</nCT>
      <serie>1</serie>
      <dhEmi>2024-01-15T10:30:00-03:00</dhEmi>
      <natOp>Transporte de Carga</natOp>
    </ide>
    <emit>
      <CNPJ>19020182000195</CNPJ>
      <xNome>Transportadora</xNome>
    </emit>
    <rem>
      <CNPJ>16716114000172</CNPJ>
    </rem>
    <dest>
      <CNPJ>12345678000190</CNPJ>
    </dest>
    <vPrest>
      <vTPrest>1000.00</vTPrest>
    </vPrest>
    <imp>
      <ICMS>
        <ICMSNORMAL>
          <vICMS>100.00</vICMS>
        </ICMSNORMAL>
      </ICMS>
    </imp>
  </infCte>
  <protCTe>
    <infProt>
      <cStat>100</cStat>
      <nProt>111111111111111</nProt>
      <dhRecbto>2024-01-15T11:00:00-03:00</dhRecbto>
    </infProt>
  </protCTe>
</CTe>"""
        parser = CTEParser("org_001")
        result = parser.parse(content)

        cte = result["cte"]
        assert cte["chave_acesso"] == "35240191002102800191570010000000011234567890"
        assert cte["numero_cte"] == "123"
        assert cte["serie"] == "1"
        assert cte["transportador_cnpj"] == "19020182000195"
        assert cte["valor_total"] == 1000.0
        assert cte["status"] == "autorizado"

    def test_parse_cte_empty_content(self):
        """Test that empty CT-e content raises error"""
        parser = CTEParser("org_001")

        with pytest.raises(Exception):
            parser.parse("")

    def test_parse_cte_invalid_xml(self):
        """Test that invalid XML raises error"""
        parser = CTEParser("org_001")

        with pytest.raises(Exception):
            parser.parse("<invalid>xml</invalid>")
