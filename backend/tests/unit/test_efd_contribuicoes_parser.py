"""
Tests for EFD Contribuições parser (EPIC 15 - AC: M100/M200/M400/M500)
"""
import pytest
from app.parsers.efd_contribuicoes import EFDContribuicoesParser, EFDContribuicoesParseError


@pytest.fixture
def minimal_efd_contrib():
    """Minimal valid EFD Contribuições with PIS and COFINS apuração"""
    return """|0000|006|0|01012018|31012018|EMPRESA TESTE LTDA|12345678000195||SP|||||1|0|
|M001|0|
|M100|01|10000,00|0,0065||0,00|65,00|0,00|0,0000|0,00|0,00|0,00|0,00|65,00|0,00|0,00|
|M100|07|5000,00|0,0000|5000,00|0,0065|32,50|0,00|0,0000|0,00|32,50|0,00|0,00|32,50|0,00|0,00|
|M200|97,50|0,00|0,00|0,00|97,50|0,00|0,00|97,50|0,00|0,00|0,00|0,00|0,00|0,00|
|M400|01|10000,00|0,0300||0,00|300,00|0,00|0,0000|0,00|0,00|0,00|0,00|300,00|0,00|0,00|
|M500|300,00|0,00|0,00|0,00|300,00|0,00|0,00|300,00|0,00|0,00|0,00|0,00|0,00|0,00|
|9999|1|
"""


def test_parser_initialization():
    """Parser deve ser instanciado com tenant_id"""
    parser = EFDContribuicoesParser(tenant_id="org_001")
    assert parser.tenant_id == "org_001"


def test_parse_empty_raises():
    """Conteúdo vazio deve lançar EFDContribuicoesParseError"""
    parser = EFDContribuicoesParser(tenant_id="org_001")
    with pytest.raises(EFDContribuicoesParseError):
        parser.parse("")


def test_parse_minimal_efd_contrib(minimal_efd_contrib):
    """Parse do arquivo mínimo deve retornar estrutura correta"""
    parser = EFDContribuicoesParser(tenant_id="org_001")
    result = parser.parse(minimal_efd_contrib)

    assert "0000" in result
    assert "M100" in result
    assert "M200" in result
    assert "M400" in result
    assert "M500" in result
    assert "metadata" in result


def test_parse_0000_header(minimal_efd_contrib):
    """Registro 0000 deve ser extraído com CNPJ e período"""
    parser = EFDContribuicoesParser(tenant_id="org_001")
    result = parser.parse(minimal_efd_contrib)

    assert result["0000"]["cod_ver"] == "006"
    assert result["0000"]["dt_ini"] == "01012018"
    assert result["0000"]["dt_fin"] == "31012018"
    assert result["0000"]["cnpj"] == "12345678000195"


def test_parse_m100_pis_credits(minimal_efd_contrib):
    """M100 deve extrair créditos PIS por CST"""
    parser = EFDContribuicoesParser(tenant_id="org_001")
    result = parser.parse(minimal_efd_contrib)

    m100_records = result["M100"]
    assert len(m100_records) == 2

    pis_cst01 = m100_records[0]
    assert pis_cst01["cst_pis"] == "01"
    assert pis_cst01["vl_bc_pis"] == 10000.0
    assert pis_cst01["vl_cred"] == 65.0


def test_parse_m200_pis_total(minimal_efd_contrib):
    """M200 deve extrair total PIS apurado"""
    parser = EFDContribuicoesParser(tenant_id="org_001")
    result = parser.parse(minimal_efd_contrib)

    m200 = result["M200"]
    assert m200 is not None
    assert m200["record_type"] == "M200"
    assert m200["vl_tot_cont_nc_per"] == 97.5
    assert m200["vl_cont_dev_per"] == 97.5


def test_parse_m400_cofins_credits(minimal_efd_contrib):
    """M400 deve extrair créditos COFINS por CST"""
    parser = EFDContribuicoesParser(tenant_id="org_001")
    result = parser.parse(minimal_efd_contrib)

    m400_records = result["M400"]
    assert len(m400_records) == 1

    cofins_cst01 = m400_records[0]
    assert cofins_cst01["cst_cofins"] == "01"
    assert cofins_cst01["vl_bc_cofins"] == 10000.0
    assert cofins_cst01["vl_cred"] == 300.0


def test_parse_m500_cofins_total(minimal_efd_contrib):
    """M500 deve extrair total COFINS apurado"""
    parser = EFDContribuicoesParser(tenant_id="org_001")
    result = parser.parse(minimal_efd_contrib)

    m500 = result["M500"]
    assert m500 is not None
    assert m500["record_type"] == "M500"
    assert m500["vl_tot_cont_nc_per"] == 300.0
    assert m500["vl_cont_dev_per"] == 300.0


def test_metadata_counts(minimal_efd_contrib):
    """Metadata deve reportar contagens corretas de registros"""
    parser = EFDContribuicoesParser(tenant_id="org_001")
    result = parser.parse(minimal_efd_contrib)

    meta = result["metadata"]
    assert meta["tenant_id"] == "org_001"
    assert meta["total_m100_records"] == 2
    assert meta["has_m200"] is True
    assert meta["total_m400_records"] == 1
    assert meta["has_m500"] is True
    assert "parsed_at" in meta
    assert "warnings" in meta


def test_parse_bytes_utf8(minimal_efd_contrib):
    """parse_bytes deve decodificar UTF-8 corretamente"""
    parser = EFDContribuicoesParser(tenant_id="org_001")
    raw = minimal_efd_contrib.encode("utf-8")
    result = parser.parse_bytes(raw)

    assert result["metadata"]["total_m100_records"] == 2


def test_parse_bytes_latin1():
    """parse_bytes deve decodificar Latin-1 corretamente"""
    content = "|0000|006|0|01012018|31012018|EMPRESA COM ACENTUAÇÃO|12345678000195||SP|||||\n|9999|1|\n"
    raw = content.encode("latin-1")

    parser = EFDContribuicoesParser(tenant_id="org_001")
    result = parser.parse_bytes(raw)

    assert result["metadata"]["total_lines_processed"] > 0


def test_m100_not_present_returns_empty_list():
    """Arquivo sem M100 deve retornar lista vazia"""
    content = """|0000|006|0|01012018|31012018|EMPRESA|12345678000195||SP|||||1|0|
|M200|0,00|0,00|0,00|0,00|0,00|0,00|0,00|0,00|0,00|0,00|0,00|0,00|0,00|0,00|
|9999|1|
"""
    parser = EFDContribuicoesParser(tenant_id="org_001")
    result = parser.parse(content)

    assert result["M100"] == []
    assert result["M400"] == []
    assert result["M200"] is not None
    assert result["M500"] is None
