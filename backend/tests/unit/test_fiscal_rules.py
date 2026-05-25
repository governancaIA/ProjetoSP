"""
Tests for fiscal validation rules (EPIC 2: 7 core rules)
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from app.models.rule_log import SeverityLevel
from app.validators.rules.fiscal_rules import (
    NfeValorDivergenteRule,
    NfeCanceladaNoSpedRule,
    SaidaSemLancamentoRule,
    CteCanceladoRule,
    IcmsDivergenteRule,
    CstIncompatiavelRule,
    CfopInvalidoRule,
)


@pytest.fixture
def mock_fiscal_document():
    """Mock FiscalDocument for testing"""
    doc = MagicMock()
    doc.id = 1
    doc.tenant_id = "org_001"
    doc.chave_acesso = "35180166047275000199550010000000011234567890"
    doc.numero_nf = "000000001"
    doc.serie = "001"
    doc.emitente_cnpj = "66047275000199"
    doc.emitente_nome = "EMPRESA TESTE LTDA"
    doc.valor_total = Decimal("1000.00")
    doc.valor_icms = Decimal("100.00")
    doc.status_nfe = "autorizado"
    doc.natureza = "saída"
    doc.items = []
    return doc


@pytest.fixture
def mock_item():
    """Mock FiscalItem for testing"""
    item = MagicMock()
    item.item_seq = 1
    item.cfop = "5101"
    item.cst = "00"
    item.valor_item = Decimal("1000.00")
    item.valor_icms = Decimal("100.00")
    item.descricao = "Item Teste"
    return item


@pytest.fixture
def test_config():
    """Test configuration"""
    return {"tolerance_brl": 0.01}


# NfeValorDivergenteRule Tests

def test_nfe_valor_divergente_conforme(mock_fiscal_document, mock_item, test_config):
    """Test NF-e value divergence within tolerance"""
    mock_item.valor_item = Decimal("1000.00")
    mock_fiscal_document.valor_total = Decimal("1000.00")
    mock_fiscal_document.items = [mock_item]

    rule = NfeValorDivergenteRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True
    assert result.severity == SeverityLevel.INFO
    assert "conforme" in result.message.lower()


def test_nfe_valor_divergente_dentro_tolerancia(mock_fiscal_document, mock_item, test_config):
    """Test NF-e value divergence within tolerance threshold"""
    mock_item.valor_item = Decimal("1000.00")
    mock_fiscal_document.valor_total = Decimal("1000.005")  # 0.005 within 0.01 tolerance
    mock_fiscal_document.items = [mock_item]

    rule = NfeValorDivergenteRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True


def test_nfe_valor_divergente_acima_tolerancia(mock_fiscal_document, mock_item, test_config):
    """Test NF-e value divergence exceeding tolerance"""
    mock_item.valor_item = Decimal("1000.00")
    mock_fiscal_document.valor_total = Decimal("999.00")  # 1.00 divergence > 0.01 tolerance
    mock_fiscal_document.items = [mock_item]

    rule = NfeValorDivergenteRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is False
    assert result.severity == SeverityLevel.WARNING
    assert "divergência" in result.message.lower()


def test_nfe_valor_divergente_sem_itens(mock_fiscal_document, test_config):
    """Test NF-e value divergence with no items"""
    rule = NfeValorDivergenteRule()
    result = rule.execute(mock_fiscal_document, [], test_config)

    assert result.passed is True


def test_nfe_valor_divergente_multiplos_itens(mock_fiscal_document, test_config):
    """Test NF-e value divergence with multiple items"""
    item1 = MagicMock()
    item1.valor_item = Decimal("500.00")

    item2 = MagicMock()
    item2.valor_item = Decimal("500.00")

    mock_fiscal_document.valor_total = Decimal("1000.00")

    rule = NfeValorDivergenteRule()
    result = rule.execute(mock_fiscal_document, [item1, item2], test_config)

    assert result.passed is True


# NfeCanceladaNoSpedRule Tests

def test_nfe_cancelada_no_sped_autorizado(mock_fiscal_document, mock_item, test_config):
    """Test authorized NF-e is not flagged"""
    mock_fiscal_document.status_nfe = "autorizado"

    rule = NfeCanceladaNoSpedRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True


def test_nfe_cancelada_no_sped_cancelado(mock_fiscal_document, mock_item, test_config):
    """Test cancelled NF-e is flagged as critical"""
    mock_fiscal_document.status_nfe = "cancelado"

    rule = NfeCanceladaNoSpedRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is False
    assert result.severity == SeverityLevel.CRITICAL
    assert "cancelada" in result.message.lower()


def test_nfe_cancelada_no_sped_denegado(mock_fiscal_document, mock_item, test_config):
    """Test denied NF-e is not flagged (different issue)"""
    mock_fiscal_document.status_nfe = "denegado"

    rule = NfeCanceladaNoSpedRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True


def test_nfe_cancelada_no_sped_nao_informado(mock_fiscal_document, mock_item, test_config):
    """Test NF-e without status is not flagged"""
    mock_fiscal_document.status_nfe = None

    rule = NfeCanceladaNoSpedRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True


# SaidaSemLancamentoRule Tests

def test_saida_sem_lancamento_saida(mock_fiscal_document, mock_item, test_config):
    """Test outgoing invoice is conforme"""
    mock_fiscal_document.natureza = "saída"

    rule = SaidaSemLancamentoRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True


def test_saida_sem_lancamento_entrada(mock_fiscal_document, mock_item, test_config):
    """Test incoming invoice is conforme (not checked)"""
    mock_fiscal_document.natureza = "entrada"

    rule = SaidaSemLancamentoRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True


def test_saida_sem_lancamento_case_insensitive(mock_fiscal_document, mock_item, test_config):
    """Test rule is case-insensitive for natureza"""
    mock_fiscal_document.natureza = "SAÍDA"

    rule = SaidaSemLancamentoRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True


# CteCanceladoRule Tests

def test_cte_cancelado_transportado_autorizado(mock_fiscal_document, mock_item, test_config):
    """Test authorized CT-e is conforme"""
    mock_fiscal_document.natureza = "transporte"
    mock_fiscal_document.status_nfe = "autorizado"

    rule = CteCanceladoRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True


def test_cte_cancelado_transportado_cancelado(mock_fiscal_document, mock_item, test_config):
    """Test cancelled CT-e is flagged as critical"""
    mock_fiscal_document.natureza = "transporte"
    mock_fiscal_document.status_nfe = "cancelado"

    rule = CteCanceladoRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is False
    assert result.severity == SeverityLevel.CRITICAL
    assert "cancelado" in result.message.lower()


def test_cte_cancelado_nao_transportado(mock_fiscal_document, mock_item, test_config):
    """Test rule doesn't apply to non-CT-e documents"""
    mock_fiscal_document.natureza = "saída"
    mock_fiscal_document.status_nfe = "cancelado"

    rule = CteCanceladoRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True


# IcmsDivergenteRule Tests

def test_icms_divergente_conforme(mock_fiscal_document, mock_item, test_config):
    """Test ICMS calculation is conforme"""
    mock_item.valor_icms = Decimal("100.00")
    mock_fiscal_document.valor_icms = Decimal("100.00")

    rule = IcmsDivergenteRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True


def test_icms_divergente_pequena_divergencia(mock_fiscal_document, mock_item, test_config):
    """Test ICMS divergence within tolerance (R$0.50/item)"""
    mock_item.valor_icms = Decimal("100.00")
    mock_fiscal_document.valor_icms = Decimal("100.30")  # Within R$0.50 tolerance

    rule = IcmsDivergenteRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True


def test_icms_divergente_acima_tolerancia(mock_fiscal_document, mock_item, test_config):
    """Test ICMS divergence exceeding tolerance"""
    mock_item.valor_icms = Decimal("100.00")
    mock_fiscal_document.valor_icms = Decimal("101.00")  # Exceeds R$0.50 tolerance

    rule = IcmsDivergenteRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is False
    assert result.severity == SeverityLevel.WARNING


def test_icms_divergente_multiplos_itens(mock_fiscal_document, test_config):
    """Test ICMS divergence with multiple items (tolerance multiplies)"""
    item1 = MagicMock()
    item1.valor_icms = Decimal("50.00")

    item2 = MagicMock()
    item2.valor_icms = Decimal("50.00")

    mock_fiscal_document.valor_icms = Decimal("100.80")  # Within R$1.00 tolerance (R$0.50 * 2 items)

    rule = IcmsDivergenteRule()
    result = rule.execute(mock_fiscal_document, [item1, item2], test_config)

    assert result.passed is True


def test_icms_divergente_sem_itens(mock_fiscal_document, test_config):
    """Test ICMS divergence with no items"""
    rule = IcmsDivergenteRule()
    result = rule.execute(mock_fiscal_document, [], test_config)

    assert result.passed is True


# CstIncompatiavelRule Tests

def test_cst_incompativel_valido(mock_fiscal_document, mock_item, test_config):
    """Test valid CST codes are conforme"""
    mock_item.cst = "00"

    rule = CstIncompatiavelRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True


def test_cst_incompativel_multiplos_validos(mock_fiscal_document, test_config):
    """Test multiple valid CST codes"""
    item1 = MagicMock()
    item1.cst = "01"

    item2 = MagicMock()
    item2.cst = "07"

    rule = CstIncompatiavelRule()
    result = rule.execute(mock_fiscal_document, [item1, item2], test_config)

    assert result.passed is True


def test_cst_incompativel_invalido(mock_fiscal_document, mock_item, test_config):
    """Test invalid CST code is flagged"""
    mock_item.cst = "99"

    rule = CstIncompatiavelRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is False
    assert result.severity == SeverityLevel.WARNING


def test_cst_incompativel_misto(mock_fiscal_document, test_config):
    """Test mix of valid and invalid CST codes"""
    item1 = MagicMock()
    item1.cst = "00"

    item2 = MagicMock()
    item2.cst = "99"

    rule = CstIncompatiavelRule()
    result = rule.execute(mock_fiscal_document, [item1, item2], test_config)

    assert result.passed is False
    assert result.severity == SeverityLevel.WARNING


def test_cst_incompativel_sem_itens(mock_fiscal_document, test_config):
    """Test CST rule with no items"""
    rule = CstIncompatiavelRule()
    result = rule.execute(mock_fiscal_document, [], test_config)

    assert result.passed is True


# CfopInvalidoRule Tests

def test_cfop_invalido_valido(mock_fiscal_document, mock_item, test_config):
    """Test valid CFOP is conforme"""
    mock_item.cfop = "5101"

    rule = CfopInvalidoRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is True


def test_cfop_invalido_multiplos_validos(mock_fiscal_document, test_config):
    """Test multiple valid CFOPs"""
    item1 = MagicMock()
    item1.cfop = "5101"

    item2 = MagicMock()
    item2.cfop = "6101"

    rule = CfopInvalidoRule()
    result = rule.execute(mock_fiscal_document, [item1, item2], test_config)

    assert result.passed is True


def test_cfop_invalido_formato_errado(mock_fiscal_document, mock_item, test_config):
    """Test CFOP with wrong format (not 4 digits)"""
    mock_item.cfop = "51"

    rule = CfopInvalidoRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is False
    assert result.severity == SeverityLevel.WARNING


def test_cfop_invalido_comeca_zero(mock_fiscal_document, mock_item, test_config):
    """Test CFOP starting with 0 is invalid"""
    mock_item.cfop = "0101"

    rule = CfopInvalidoRule()
    result = rule.execute(mock_fiscal_document, [mock_item], test_config)

    assert result.passed is False
    assert result.severity == SeverityLevel.WARNING


def test_cfop_invalido_sem_itens(mock_fiscal_document, test_config):
    """Test CFOP rule with no items"""
    rule = CfopInvalidoRule()
    result = rule.execute(mock_fiscal_document, [], test_config)

    assert result.passed is True


# Integration: All rules registered and instantiable

def test_all_rules_registered():
    """Test that all 7 rules are registered and retrievable"""
    from app.validators.rules.registry import get_active_rules

    rules = get_active_rules()
    rule_ids = [r.rule_id for r in rules]

    # Verify all 7 core rules are registered
    assert "nfe_valor_divergente" in rule_ids
    assert "nfe_cancelada_no_sped" in rule_ids
    assert "saida_sem_lancamento" in rule_ids
    assert "cte_cancelado" in rule_ids
    assert "icms_divergente" in rule_ids
    assert "cst_incompativel" in rule_ids
    assert "cfop_invalido" in rule_ids


def test_rule_versions_are_semantic():
    """Test that all rules have semantic version format"""
    from app.validators.rules.registry import get_active_rules

    rules = get_active_rules()

    for rule in rules:
        assert rule.rule_version, f"{rule.rule_id} has no version"
        parts = rule.rule_version.split(".")
        assert len(parts) == 3, f"{rule.rule_id} version {rule.rule_version} not semantic"
        for part in parts:
            assert part.isdigit(), f"{rule.rule_id} version {rule.rule_version} not numeric"
