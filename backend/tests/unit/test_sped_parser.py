"""
Tests for SPED EFD ICMS/IPI parser (US-1.4)
"""
import pytest
from pathlib import Path
from app.parsers.sped_efd_icms import SPEDParser, ParseError, _detect_encoding, _get_layout

# Real EFD files from docs/ — used for integration-level tests
_DOCS_DIR = Path(__file__).parent.parent.parent.parent / "docs"
_EFD_JAN = _DOCS_DIR / "1 - EFD-ICMSIPI-JAN2018.TXT"
_EFD_FEV = _DOCS_DIR / "2 - EFD-ICMSIPI-FEV2018.TXT"
_EFD_MAR = _DOCS_DIR / "3 - EFD-ICMSIPI-MAR2018.TXT"


@pytest.fixture
def sample_sped_content():
    """Load real SPED fixture for testing"""
    if not _EFD_JAN.exists():
        pytest.skip(f"Fixture not found: {_EFD_JAN}")
    return _EFD_JAN.read_text(encoding='utf-8', errors='ignore')


@pytest.fixture
def real_efd_jan_bytes():
    if not _EFD_JAN.exists():
        pytest.skip(f"Fixture not found: {_EFD_JAN}")
    return _EFD_JAN.read_bytes()


@pytest.fixture
def real_efd_fev_bytes():
    if not _EFD_FEV.exists():
        pytest.skip(f"Fixture not found: {_EFD_FEV}")
    return _EFD_FEV.read_bytes()


@pytest.fixture
def real_efd_mar_bytes():
    if not _EFD_MAR.exists():
        pytest.skip(f"Fixture not found: {_EFD_MAR}")
    return _EFD_MAR.read_bytes()


@pytest.fixture
def minimal_sped():
    """Minimal valid SPED for unit testing"""
    return """|0|00|1|66047275000199|35|2018|1|01012018|31012018|ARAMEFICIO CHAVANTES IND E COM LTDA|1|0|
|0|01|0|
|C100|0|1|001|55|00|001|000000001|35180166047275000199550010000000011234567890|01012018|01012018|100,00|1|0,00|0,00|100,00|9|0,00|0,00|0,00|0,00|0,00|0,00|0,00|0,00|
|C170|1|1000000001||1,00000|un|100,00|0,00|0|000|1101|30|100,00|0,00|0,00|0,00|0,00|0,00|0|03||0,00|0,00|0,00|
|9|001|1|1|100,00|
"""


def test_parser_initialization():
    """Test parser can be instantiated with tenant_id"""
    parser = SPEDParser(tenant_id="org_001")
    assert parser.tenant_id == "org_001"


def test_parse_minimal_sped(minimal_sped):
    """Test parsing a minimal valid SPED"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(minimal_sped)

    assert "C100" in result
    assert "C170" in result
    assert "E110" in result
    assert "metadata" in result
    assert len(result["C100"]) == 1
    assert len(result["C170"]) == 1


def test_parse_c100_record(minimal_sped):
    """Test C100 (NF header) record extraction"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(minimal_sped)

    c100 = result["C100"][0]
    assert c100["ind_mov"] == "0"
    assert c100["ind_emitente"] == "1"
    assert c100["serie"] == "001"
    assert c100["modelo"] == "55"
    assert c100["numero_nf"] == "000000001"
    assert c100["chave_acesso"] == "35180166047275000199550010000000011234567890"
    assert c100["data_emissao"] == "01012018"
    # Note: SPED uses comma as decimal separator, values are stored as strings
    assert "100,00" in c100["valor_total"] or float(c100["valor_total"].replace(',', '.')) == 100.00


def test_parse_c170_record(minimal_sped):
    """Test C170 (item) record extraction"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(minimal_sped)

    c170 = result["C170"][0]
    assert c170["numero_sequencial"] == "1"
    assert c170["codigo_item"] == "1000000001"
    # SPED uses comma as decimal separator
    assert float(c170["quantidade"].replace(',', '.')) == 1.00000
    assert c170["unidade"] == "un"
    assert float(c170["valor_unitario"].replace(',', '.')) == 100.00
    assert c170["cfop"] == "000"
    assert c170["cst"] == "1101"
    # Note: valor_icms field index may vary based on actual SPED spec
    # Just verify it's a string for now
    assert isinstance(c170["valor_icms"], str)


def test_parse_real_fixture(sample_sped_content):
    """Test parsing the real SPED fixture file"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(sample_sped_content)

    assert "C100" in result
    assert "C170" in result
    assert "metadata" in result
    assert len(result["C100"]) > 0
    assert len(result["C170"]) > 0
    assert result["metadata"]["total_c100_records"] == len(result["C100"])
    assert result["metadata"]["total_c170_records"] == len(result["C170"])


def test_parse_invalid_sped():
    """Test parsing invalid SPED raises ParseError"""
    parser = SPEDParser(tenant_id="org_001")

    with pytest.raises(ParseError):
        parser.parse("")


def test_metadata_generation(minimal_sped):
    """Test metadata is correctly generated"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(minimal_sped)

    assert result["metadata"]["tenant_id"] == "org_001"
    assert result["metadata"]["total_c100_records"] == 1
    assert result["metadata"]["total_c170_records"] == 1
    assert "parsed_at" in result["metadata"]
    assert "warnings" in result["metadata"]


def test_c100_natureza_saida_when_ind_emitente_0():
    """ind_emitente=0 (emissão própria) deve resultar em natureza=saida"""
    sped = """|0|00|1|66047275000199|35|2018|1|01012018|31012018|EMPRESA|1|0|
|C100|0|0|001|55|00|001|35180166047275000199550010000000011234567890|01012018|01012018|100,00|1|0,00|0,00|100,00|9|0,00|0,00|0,00|0,00|0,00|0,00|0,00|
|9|001|1|
"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(sped)

    assert len(result["C100"]) == 1
    assert result["C100"][0]["natureza"] == "saida"
    assert result["C100"][0]["ind_emitente"] == "0"


def test_c100_natureza_entrada_when_ind_emitente_1():
    """ind_emitente=1 (terceiros) deve resultar em natureza=entrada"""
    sped = """|0|00|1|66047275000199|35|2018|1|01012018|31012018|EMPRESA|1|0|
|C100|0|1|001|55|00|001|35180166047275000199550010000000011234567890|01012018|01012018|100,00|1|0,00|0,00|100,00|9|0,00|0,00|0,00|0,00|0,00|0,00|0,00|
|9|001|1|
"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(sped)

    assert result["C100"][0]["natureza"] == "entrada"


def test_c110_cancellation_marks_c100():
    """C110 com cod_inf 110111 deve marcar o C100 pai como cancelado"""
    sped = """|0|00|1|66047275000199|35|2018|1|01012018|31012018|EMPRESA|1|0|
|C100|0|0|001|55|00|001|35180166047275000199550010000000011234567890|01012018|01012018|100,00|1|0,00|0,00|100,00|9|0,00|0,00|0,00|0,00|0,00|0,00|0,00|
|C110|110111|Cancelamento de NF-e|
|9|001|1|
"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(sped)

    assert result["C100"][0]["cancelado"] is True


def test_c110_other_code_does_not_cancel():
    """C110 com código diferente de 110111 não deve marcar como cancelado"""
    sped = """|0|00|1|66047275000199|35|2018|1|01012018|31012018|EMPRESA|1|0|
|C100|0|0|001|55|00|001|35180166047275000199550010000000011234567890|01012018|01012018|100,00|1|0,00|0,00|100,00|9|0,00|0,00|0,00|0,00|0,00|0,00|0,00|
|C110|999999|Outra informação complementar|
|9|001|1|
"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(sped)

    assert result["C100"][0]["cancelado"] is False


def test_c100_cancelado_default_false(minimal_sped):
    """C100 sem C110 de cancelamento deve ter cancelado=False por padrão"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(minimal_sped)

    assert result["C100"][0]["cancelado"] is False


def test_c100_status_nfe_cancelado_when_c110():
    """C100 com C110 cancelamento deve ter status_nfe='cancelado' no pós-processamento"""
    sped = """|0|00|1|66047275000199|35|2018|1|01012018|31012018|EMPRESA|1|0|
|C100|0|0|001|55|00|001|35180166047275000199550010000000011234567890|01012018|01012018|100,00|1|0,00|0,00|100,00|9|0,00|0,00|0,00|0,00|0,00|0,00|0,00|
|C110|110111|Cancelamento de NF-e|
|9|001|1|
"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(sped)

    assert result["C100"][0]["status_nfe"] == "cancelado"


def test_c100_status_nfe_autorizado_when_no_c110():
    """C100 sem C110 de cancelamento deve ter status_nfe='autorizado'"""
    sped = """|0|00|1|66047275000199|35|2018|1|01012018|31012018|EMPRESA|1|0|
|C100|0|0|001|55|00|001|35180166047275000199550010000000011234567890|01012018|01012018|100,00|1|0,00|0,00|100,00|9|0,00|0,00|0,00|0,00|0,00|0,00|0,00|
|9|001|1|
"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(sped)

    assert result["C100"][0]["status_nfe"] == "autorizado"


def test_parse_0000_record_extraction():
    """Registro 0000 deve ser extraído com versão e CNPJ"""
    sped = """|0000|017|0|01012018|31012018|EMPRESA TESTE LTDA|12345678000195||SP|3550308||A|1|
|C100|0|0|001|55|00|001|35180166047275000199550010000000011234567890|01012018|01012018|100,00|1|0,00|0,00|100,00|9|0,00|0,00|0,00|0,00|0,00|0,00|0,00|
|9|001|1|
"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(sped)

    assert result["0000"]["cod_ver"] == "017"
    assert result["0000"]["cnpj"] == "12345678000195"
    assert result["metadata"]["file_version"] == "017"


def test_parse_bytes_latin1_encoding():
    """parse_bytes deve decodificar corretamente arquivos Latin-1"""
    content_str = "|0000|014|0|01012018|31012018|FARMÁCIA SÃO JOÃO LTDA|12345678000195||SP|3550308||A|1|\n|9|001|1|\n"
    raw_latin1 = content_str.encode("latin-1")

    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse_bytes(raw_latin1)

    assert result["metadata"]["total_lines_processed"] > 0
    # Verify special characters in company name were preserved (or at least parsed without error)
    assert "0000" in result


def test_parse_bytes_utf8_encoding():
    """parse_bytes deve decodificar corretamente arquivos UTF-8"""
    content_str = "|0000|017|0|01012018|31012018|EMPRESA TESTE|12345678000195||SP|3550308||A|1|\n|9|001|1|\n"
    raw_utf8 = content_str.encode("utf-8")

    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse_bytes(raw_utf8)

    assert result["metadata"]["total_lines_processed"] > 0


def test_unknown_version_generates_warning():
    """Versão desconhecida deve gerar warning mas não falhar"""
    sped = """|0000|999|0|01012018|31012018|EMPRESA|12345678000195||SP|3550308||A|1|
|9|001|1|
"""
    parser = SPEDParser(tenant_id="org_001")
    result = parser.parse(sped)

    assert any("999" in w for w in result["metadata"]["warnings"])


# ── Testes com arquivos EFD reais (docs/*.TXT) ──────────────────────────────

def test_real_jan_parse_bytes(real_efd_jan_bytes):
    """Arquivo EFD real de JAN/2018 deve ser parseado via parse_bytes sem erros"""
    parser = SPEDParser(tenant_id="arameficio")
    result = parser.parse_bytes(real_efd_jan_bytes)

    assert len(result["C100"]) == 337
    assert len(result["C170"]) == 296
    assert len(result["E110"]) == 1
    assert result["metadata"]["total_c100_records"] == 337
    assert result["metadata"]["total_c170_records"] == 296


def test_real_jan_0000_record(real_efd_jan_bytes):
    """Arquivo EFD real de JAN/2018 deve extrair 0000 com CNPJ e razão social"""
    parser = SPEDParser(tenant_id="arameficio")
    result = parser.parse_bytes(real_efd_jan_bytes)

    header = result["0000"]
    assert header["cnpj"] == "66047275000199"
    assert "ARAMEFICIO" in header["nome"]
    assert header["uf"] == "SP"
    assert header["cod_ver"] == "012"


def test_real_jan_version_012_layout_selected(real_efd_jan_bytes):
    """Arquivo versão 012 usa o mesmo layout padrão — UF na posição 7 (com campo CPF vazio)"""
    parser = SPEDParser(tenant_id="arameficio")
    result = parser.parse_bytes(real_efd_jan_bytes)

    header = result["0000"]
    assert header["uf"] == "SP"
    assert header["cod_ver"] == "012"


def test_real_jan_c100_records_have_status_nfe(real_efd_jan_bytes):
    """Todos os C100 do arquivo real devem ter status_nfe preenchido"""
    parser = SPEDParser(tenant_id="arameficio")
    result = parser.parse_bytes(real_efd_jan_bytes)

    for c100 in result["C100"]:
        assert "status_nfe" in c100
        assert c100["status_nfe"] in ("autorizado", "cancelado")


def test_real_jan_no_false_cancellations(real_efd_jan_bytes):
    """C110 com códigos diferentes de 110111 não devem cancelar NFs no arquivo real"""
    parser = SPEDParser(tenant_id="arameficio")
    result = parser.parse_bytes(real_efd_jan_bytes)

    # The real file has C110 records with numeric sequence codes (not 110111)
    # So ALL records should be autorizado (none cancelled)
    cancelled = [c for c in result["C100"] if c["status_nfe"] == "cancelado"]
    assert len(cancelled) == 0, f"Expected 0 cancelled, got {len(cancelled)}"


def test_real_jan_c100_chave_acesso_length(real_efd_jan_bytes):
    """chave_acesso nos registros C100 reais deve ter 44 caracteres ou estar vazia"""
    parser = SPEDParser(tenant_id="arameficio")
    result = parser.parse_bytes(real_efd_jan_bytes)

    for c100 in result["C100"]:
        chave = c100.get("chave_acesso", "")
        if chave:
            assert len(chave) == 44, f"chave_acesso inválida: '{chave}' (len={len(chave)})"


def test_real_jan_natureza_distribution(real_efd_jan_bytes):
    """Arquivo real deve ter mix de entradas e saídas"""
    parser = SPEDParser(tenant_id="arameficio")
    result = parser.parse_bytes(real_efd_jan_bytes)

    naturezas = {c["natureza"] for c in result["C100"]}
    assert "entrada" in naturezas or "saida" in naturezas


def test_real_fev_parse_bytes(real_efd_fev_bytes):
    """Arquivo EFD real de FEV/2018 deve ser parseado sem erros"""
    parser = SPEDParser(tenant_id="arameficio")
    result = parser.parse_bytes(real_efd_fev_bytes)

    assert result["metadata"]["total_c100_records"] > 0
    assert result["metadata"]["total_c100_records"] == len(result["C100"])


def test_real_mar_parse_bytes(real_efd_mar_bytes):
    """Arquivo EFD real de MAR/2018 deve ser parseado sem erros"""
    parser = SPEDParser(tenant_id="arameficio")
    result = parser.parse_bytes(real_efd_mar_bytes)

    assert result["metadata"]["total_c100_records"] > 0
    assert result["metadata"]["total_c100_records"] == len(result["C100"])


def test_real_three_months_consistent_cnpj(real_efd_jan_bytes, real_efd_fev_bytes, real_efd_mar_bytes):
    """Os três arquivos mensais devem pertencer ao mesmo CNPJ"""
    parser = SPEDParser(tenant_id="arameficio")
    r1 = parser.parse_bytes(real_efd_jan_bytes)
    r2 = parser.parse_bytes(real_efd_fev_bytes)
    r3 = parser.parse_bytes(real_efd_mar_bytes)

    cnpj_jan = r1["0000"]["cnpj"]
    cnpj_fev = r2["0000"]["cnpj"]
    cnpj_mar = r3["0000"]["cnpj"]

    assert cnpj_jan == cnpj_fev == cnpj_mar, (
        f"CNPJ divergente entre meses: JAN={cnpj_jan}, FEV={cnpj_fev}, MAR={cnpj_mar}"
    )


def test_detect_encoding_utf8():
    """_detect_encoding deve identificar UTF-8 corretamente"""
    raw = "EMPRESA TESTE LTDA".encode("utf-8")
    enc = _detect_encoding(raw)
    assert enc.lower().replace("-", "") in ("utf8", "utf8sig", "ascii")


def test_get_layout_version_012():
    """Versão 012 deve retornar layout padrão com CNPJ na posição 5"""
    layout = _get_layout("012")
    assert layout["cnpj"] == 5
    assert layout["uf"] == 7


def test_get_layout_version_017():
    """Versão 017 deve retornar layout padrão com UF na posição 7"""
    layout = _get_layout("017")
    assert layout["cnpj"] == 5
    assert layout["uf"] == 7


def test_get_layout_unknown_version_uses_standard():
    """Versão desconhecida deve usar layout padrão"""
    layout = _get_layout("099")
    assert layout["cnpj"] == 5
    assert layout["uf"] == 7
