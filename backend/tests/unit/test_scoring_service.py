"""
Tests for ScoringService (EPIC 4: Scoring)
"""
import pytest
from decimal import Decimal
from datetime import datetime, date
from unittest.mock import MagicMock, patch

from app.models.rule_log import SeverityLevel, RuleExecutionLog
from app.services.scoring_service import ScoringService, AlertSeverity


@pytest.fixture
def mock_fiscal_document():
    """Mock FiscalDocument for scoring tests"""
    doc = MagicMock()
    doc.id = 1
    doc.tenant_id = "org_001"
    doc.chave_acesso = "35180166047275000199550010000000011234567890"
    doc.numero_nf = "000000001"
    doc.valor_total = Decimal("1000.00")
    doc.valor_icms = Decimal("100.00")
    doc.data_emissao = date(2024, 1, 15)
    return doc


@pytest.fixture
def mock_rule_log_passed():
    """Mock passed rule log"""
    log = MagicMock(spec=RuleExecutionLog)
    log.id = 1
    log.rule_id = "nfe_valor_divergente"
    log.rule_version = "1.0.0"
    log.passed = True
    log.severity = SeverityLevel.INFO
    log.message = "Valor conforme"
    log.input_snapshot = None
    log.config_applied = None
    log.get_input_snapshot = MagicMock(return_value={})
    return log


@pytest.fixture
def mock_rule_log_failed_nfe_divergencia():
    """Mock failed NF-e divergence rule log"""
    log = MagicMock(spec=RuleExecutionLog)
    log.id = 2
    log.rule_id = "nfe_valor_divergente"
    log.rule_version = "1.0.0"
    log.passed = False
    log.severity = SeverityLevel.WARNING
    log.message = "Divergência de valor"
    log.input_snapshot = {"divergencia": 50.00}
    log.config_applied = None
    log.get_input_snapshot = MagicMock(return_value={"divergencia": 50.00})
    log.fiscal_document_id = 1
    return log


@pytest.fixture
def mock_rule_log_failed_critical():
    """Mock failed critical rule log"""
    log = MagicMock(spec=RuleExecutionLog)
    log.id = 3
    log.rule_id = "nfe_cancelada_no_sped"
    log.rule_version = "1.0.0"
    log.passed = False
    log.severity = SeverityLevel.CRITICAL
    log.message = "NF-e cancelada ainda no SPED"
    log.input_snapshot = {}
    log.config_applied = None
    log.get_input_snapshot = MagicMock(return_value={})
    log.fiscal_document_id = 1
    return log


# Test: Calculate Alert Severity

def test_calculate_alert_severity_passed_rule(mock_fiscal_document, mock_rule_log_passed):
    """Test passed rule returns INFORMATIVE severity"""
    severity, exposure = ScoringService.calculate_alert_severity(
        mock_rule_log_passed, mock_fiscal_document
    )

    assert severity == AlertSeverity.INFORMATIVE
    assert exposure == Decimal("0.00")


def test_calculate_alert_severity_critical_rule(mock_fiscal_document, mock_rule_log_failed_critical):
    """Test CRITICAL rule severity maps to CRITICAL alert"""
    severity, exposure = ScoringService.calculate_alert_severity(
        mock_rule_log_failed_critical, mock_fiscal_document
    )

    assert severity == AlertSeverity.CRITICAL
    assert exposure > Decimal("0.00")  # Should have exposure


def test_calculate_alert_severity_warning_high_exposure(mock_fiscal_document, mock_rule_log_failed_nfe_divergencia):
    """Test WARNING rule with high exposure maps to HIGH alert"""
    mock_rule_log_failed_nfe_divergencia.input_snapshot = {"divergencia": 5000.00}
    mock_rule_log_failed_nfe_divergencia.get_input_snapshot = MagicMock(
        return_value={"divergencia": 5000.00}
    )

    severity, exposure = ScoringService.calculate_alert_severity(
        mock_rule_log_failed_nfe_divergencia, mock_fiscal_document
    )

    assert severity == AlertSeverity.HIGH
    assert exposure > Decimal("1000.00")


def test_calculate_alert_severity_warning_low_exposure(mock_fiscal_document, mock_rule_log_failed_nfe_divergencia):
    """Test WARNING rule with low exposure maps to MEDIUM alert (min is R$500)"""
    severity, exposure = ScoringService.calculate_alert_severity(
        mock_rule_log_failed_nfe_divergencia, mock_fiscal_document
    )

    # With divergence R$50, expected exposure = 50 * 0.75 = R$37.50, clamped to min R$500
    assert severity == AlertSeverity.MEDIUM  # R$500 >= R$100
    assert exposure == Decimal("500.00")


# Test: Calculate Exposure

def test_calculate_exposure_nfe_valor_divergente(mock_fiscal_document, mock_rule_log_failed_nfe_divergencia):
    """Test exposure calculation for NF-e divergence rule"""
    penalty_config = ScoringService.PENALTY_BASE_RATES["nfe_valor_divergente"]

    exposure = ScoringService._calculate_exposure(
        mock_rule_log_failed_nfe_divergencia,
        mock_fiscal_document,
        penalty_config,
    )

    # Expected: divergencia (50.00) * rate (0.75) = 37.50, but clamped to min (500.00)
    assert exposure == Decimal("500.00")


def test_calculate_exposure_nfe_cancelada(mock_fiscal_document, mock_rule_log_failed_critical):
    """Test exposure calculation for cancelled NF-e rule"""
    penalty_config = ScoringService.PENALTY_BASE_RATES["nfe_cancelada_no_sped"]

    exposure = ScoringService._calculate_exposure(
        mock_rule_log_failed_critical,
        mock_fiscal_document,
        penalty_config,
    )

    # Expected: valor_total (1000.00) * rate (1.00) = 1000.00
    assert exposure == Decimal("1000.00")


def test_calculate_exposure_clamped_to_max(mock_fiscal_document, mock_rule_log_failed_critical):
    """Test exposure calculation respects max penalty"""
    mock_fiscal_document.valor_total = Decimal("1000000.00")  # Very large invoice
    penalty_config = ScoringService.PENALTY_BASE_RATES["nfe_cancelada_no_sped"]

    exposure = ScoringService._calculate_exposure(
        mock_rule_log_failed_critical,
        mock_fiscal_document,
        penalty_config,
    )

    # Should be clamped to max (100000.00)
    assert exposure == Decimal("100000.00")


# Test: Get Document Score
# (Integration-level tests deferred to test_integration_scoring.py)


# Test: Get Period Score

def test_get_period_score_no_documents():
    """Test period score when no documents in period"""
    mock_db = MagicMock()

    # Mock empty fiscal documents query
    mock_db.query.return_value.filter.return_value.all.return_value = []

    result = ScoringService.get_period_score(mock_db, "org_001", 2024, 1)

    assert result["period"] == "2024-01"
    assert result["documents_processed"] == 0
    assert result["period_score"] == 100
    assert result["total_exposure"] == 0.00


# Test: Priority Queue

def test_get_alert_prioritization_queue_empty():
    """Test priority queue when no alerts"""
    mock_db = MagicMock()

    # Mock empty rule logs
    mock_db.query.return_value.filter.return_value.all.return_value = []

    result = ScoringService.get_alert_prioritization_queue(mock_db, "org_001", limit=50)

    assert len(result) == 0


# Test: Penalty Rate Validation

def test_penalty_base_rates_configured():
    """Verify penalty rates are configured for all core rules"""
    expected_rules = [
        "nfe_valor_divergente",
        "nfe_cancelada_no_sped",
        "saida_sem_lancamento",
        "cte_cancelado",
        "icms_divergente",
        "cst_incompativel",
        "cfop_invalido",
    ]

    for rule_id in expected_rules:
        assert rule_id in ScoringService.PENALTY_BASE_RATES
        config = ScoringService.PENALTY_BASE_RATES[rule_id]
        assert "rate" in config
        assert "min" in config
        assert "max" in config


# Test: Alert Severity Enum

def test_alert_severity_values():
    """Test AlertSeverity enum has expected values"""
    assert AlertSeverity.CRITICAL.value == "CRITICAL"
    assert AlertSeverity.HIGH.value == "HIGH"
    assert AlertSeverity.MEDIUM.value == "MEDIUM"
    assert AlertSeverity.LOW.value == "LOW"
    assert AlertSeverity.INFORMATIVE.value == "INFORMATIVE"


# Test: Exposure Calculation Edge Cases

def test_calculate_exposure_zero_divergence(mock_fiscal_document):
    """Test exposure when divergence is zero"""
    log = MagicMock(spec=RuleExecutionLog)
    log.rule_id = "nfe_valor_divergente"
    log.get_input_snapshot = MagicMock(return_value={"divergencia": 0})

    penalty_config = ScoringService.PENALTY_BASE_RATES["nfe_valor_divergente"]

    exposure = ScoringService._calculate_exposure(log, mock_fiscal_document, penalty_config)

    # Should be clamped to minimum (500.00)
    assert exposure == Decimal("500.00")


def test_calculate_exposure_unknown_rule(mock_fiscal_document):
    """Test exposure calculation for unknown rule ID"""
    log = MagicMock(spec=RuleExecutionLog)
    log.rule_id = "unknown_future_rule"
    log.get_input_snapshot = MagicMock(return_value={})

    penalty_config = {"rate": 0.50, "min": 100, "max": 10000}

    exposure = ScoringService._calculate_exposure(log, mock_fiscal_document, penalty_config)

    # Should use conservative default: valor_total * rate * 0.05
    # = 1000.00 * 0.50 * 0.05 = 25.00, clamped to min (100.00)
    assert exposure == Decimal("100.00")
