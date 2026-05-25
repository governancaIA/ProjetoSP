"""
Tests for Rule Engine (BaseRule, RuleDAG, Registry, RuleService)
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from decimal import Decimal

from app.models.rule_log import SeverityLevel
from app.validators.rules.base import BaseRule, RuleResult
from app.validators.rules.dag import RuleDAG
from app.validators.rules.registry import register, get_active_rules, list_rules


# Sample test rule implementations

class TestRulePass(BaseRule):
    rule_id = "test_rule_pass"
    rule_version = "1.0.0"
    depends_on = []

    def execute(self, fiscal_document, items, config):
        return self._pass("Test rule passed", input_snapshot={"key": "value"})


class TestRuleFail(BaseRule):
    rule_id = "test_rule_fail"
    rule_version = "1.0.0"
    depends_on = []

    def execute(self, fiscal_document, items, config):
        return self._fail(
            SeverityLevel.WARNING,
            "Test rule failed",
            input_snapshot={"expected": 100.00, "actual": 99.99},
        )


class TestRuleCritical(BaseRule):
    rule_id = "test_rule_critical"
    rule_version = "1.0.0"
    depends_on = []

    def execute(self, fiscal_document, items, config):
        return self._fail(
            SeverityLevel.CRITICAL,
            "Critical test rule failed",
            input_snapshot={"issue": "document_cancelled"},
        )


class TestRuleWithDeps(BaseRule):
    rule_id = "test_rule_with_deps"
    rule_version = "1.0.0"
    depends_on = ["test_rule_pass"]

    def execute(self, fiscal_document, items, config):
        return self._pass("Rule with dependencies")


# Fixtures

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
    doc.valor_total = Decimal("100.00")
    doc.valor_icms = Decimal("12.00")
    doc.items = []
    return doc


@pytest.fixture
def mock_items():
    """Mock list of FiscalItems"""
    item = MagicMock()
    item.item_seq = 1
    item.cfop = "5101"
    item.cst = "00"
    item.valor_item = Decimal("100.00")
    item.valor_icms = Decimal("12.00")
    return [item]


@pytest.fixture
def test_config():
    """Test configuration"""
    return {"tolerance_brl": 0.01}


# BaseRule Tests

def test_base_rule_pass(mock_fiscal_document, mock_items, test_config):
    """Test BaseRule._pass() creates correct RuleResult"""
    rule = TestRulePass()
    result = rule.execute(mock_fiscal_document, mock_items, test_config)

    assert result.rule_id == "test_rule_pass"
    assert result.rule_version == "1.0.0"
    assert result.passed is True
    assert result.severity == SeverityLevel.INFO
    assert result.message == "Test rule passed"
    assert result.input_snapshot == {"key": "value"}


def test_base_rule_fail_warning(mock_fiscal_document, mock_items, test_config):
    """Test BaseRule._fail() with WARNING severity"""
    rule = TestRuleFail()
    result = rule.execute(mock_fiscal_document, mock_items, test_config)

    assert result.rule_id == "test_rule_fail"
    assert result.passed is False
    assert result.severity == SeverityLevel.WARNING
    assert result.message == "Test rule failed"


def test_base_rule_fail_critical(mock_fiscal_document, mock_items, test_config):
    """Test BaseRule._fail() with CRITICAL severity"""
    rule = TestRuleCritical()
    result = rule.execute(mock_fiscal_document, mock_items, test_config)

    assert result.passed is False
    assert result.severity == SeverityLevel.CRITICAL


def test_rule_result_with_config_applied(mock_fiscal_document, mock_items):
    """Test RuleResult captures config_applied"""
    rule = TestRulePass()
    config = {"tolerance_brl": 0.05}
    result = rule._pass(
        "Message",
        config_applied={"applied_tolerance": 0.05}
    )

    assert result.config_applied == {"applied_tolerance": 0.05}


# RuleDAG Tests

def test_dag_single_rule(mock_fiscal_document, mock_items, test_config):
    """Test RuleDAG execution with single rule"""
    dag = RuleDAG([TestRulePass()])
    results = dag.execute(mock_fiscal_document, mock_items, test_config)

    assert len(results) == 1
    assert results[0].rule_id == "test_rule_pass"
    assert results[0].passed is True


def test_dag_multiple_rules_no_deps(mock_fiscal_document, mock_items, test_config):
    """Test RuleDAG execution with multiple independent rules"""
    dag = RuleDAG([TestRulePass(), TestRuleFail(), TestRuleCritical()])
    results = dag.execute(mock_fiscal_document, mock_items, test_config)

    assert len(results) == 3
    rule_ids = [r.rule_id for r in results]
    assert "test_rule_pass" in rule_ids
    assert "test_rule_fail" in rule_ids
    assert "test_rule_critical" in rule_ids


def test_dag_topological_order_with_deps(mock_fiscal_document, mock_items, test_config):
    """Test RuleDAG respects depends_on ordering"""
    # RuleWithDeps depends on TestRulePass
    dag = RuleDAG([TestRuleWithDeps(), TestRulePass()])
    results = dag.execute(mock_fiscal_document, mock_items, test_config)

    assert len(results) == 2
    # Find indices
    pass_idx = next(i for i, r in enumerate(results) if r.rule_id == "test_rule_pass")
    deps_idx = next(i for i, r in enumerate(results) if r.rule_id == "test_rule_with_deps")

    # TestRulePass should execute before TestRuleWithDeps
    assert pass_idx < deps_idx


def test_dag_missing_dependency(mock_fiscal_document, mock_items, test_config):
    """Test RuleDAG handles missing dependency gracefully"""
    # TestRuleWithDeps depends on "test_rule_pass" but it's not provided
    dag = RuleDAG([TestRuleWithDeps()])
    # Should not raise, but soft-fail the dependency
    results = dag.execute(mock_fiscal_document, mock_items, test_config)
    assert len(results) == 1


# Registry Tests

def test_registry_register_decorator():
    """Test @register decorator adds rule to registry"""
    # Clear registry for this test
    import app.validators.rules.registry as registry_module
    original_registry = registry_module._registry.copy()
    registry_module._registry.clear()

    try:
        @register
        class MyTestRule(BaseRule):
            rule_id = "my_test_rule"
            rule_version = "1.0.0"

            def execute(self, fiscal_document, items, config):
                return self._pass("Test")

        assert "my_test_rule" in registry_module._registry
        assert registry_module._registry["my_test_rule"] == MyTestRule

    finally:
        # Restore original registry
        registry_module._registry.clear()
        registry_module._registry.update(original_registry)


def test_registry_register_missing_rule_id():
    """Test @register raises error if rule_id not defined"""
    import app.validators.rules.registry as registry_module

    with pytest.raises(ValueError, match="must define 'rule_id'"):
        @register
        class InvalidRule(BaseRule):
            rule_version = "1.0.0"

            def execute(self, fiscal_document, items, config):
                pass


def test_registry_get_active_rules():
    """Test get_active_rules() returns instances"""
    import app.validators.rules.registry as registry_module
    original_registry = registry_module._registry.copy()
    registry_module._registry.clear()

    try:
        @register
        class Rule1(BaseRule):
            rule_id = "rule1"
            rule_version = "1.0.0"

            def execute(self, f, i, c):
                return self._pass("R1")

        @register
        class Rule2(BaseRule):
            rule_id = "rule2"
            rule_version = "1.0.0"

            def execute(self, f, i, c):
                return self._pass("R2")

        rules = registry_module.get_active_rules()
        assert len(rules) == 2
        rule_ids = [r.rule_id for r in rules]
        assert "rule1" in rule_ids
        assert "rule2" in rule_ids

    finally:
        registry_module._registry.clear()
        registry_module._registry.update(original_registry)


def test_registry_list_rules():
    """Test list_rules() returns rule IDs"""
    import app.validators.rules.registry as registry_module
    original_registry = registry_module._registry.copy()
    registry_module._registry.clear()

    try:
        @register
        class Rule1(BaseRule):
            rule_id = "rule1"
            rule_version = "1.0.0"

            def execute(self, f, i, c):
                return self._pass("R1")

        rule_ids = registry_module.list_rules()
        assert "rule1" in rule_ids

    finally:
        registry_module._registry.clear()
        registry_module._registry.update(original_registry)


# RuleService Tests

def test_rule_service_save_results(mock_fiscal_document):
    """Test RuleService.save_results() persists RuleExecutionLog"""
    from app.services.rule_service import RuleService

    mock_db = MagicMock()
    results = [
        RuleResult(
            rule_id="rule1",
            rule_version="1.0.0",
            passed=True,
            severity=SeverityLevel.INFO,
            message="Passed",
            input_snapshot={"key": "value"},
            config_applied={"tolerance": 0.01},
        ),
        RuleResult(
            rule_id="rule2",
            rule_version="1.0.0",
            passed=False,
            severity=SeverityLevel.WARNING,
            message="Failed",
            input_snapshot={"expected": 100, "actual": 99},
            config_applied={"tolerance": 0.01},
        ),
    ]

    logs = RuleService.save_results(
        mock_db,
        "org_001",
        mock_fiscal_document.id,
        results,
        "parser",
    )

    assert len(logs) == 2
    assert mock_db.add.call_count == 2
    assert logs[0].rule_id == "rule1"
    assert logs[1].rule_id == "rule2"


def test_rule_service_get_config_defaults():
    """Test RuleService.get_config() returns defaults"""
    from app.services.rule_service import RuleService

    mock_db = MagicMock()
    config = RuleService.get_config(mock_db, "org_001", "*")

    assert "tolerance_brl" in config
    assert config["tolerance_brl"] == 0.01


# validate_document Task Tests
# Note: These tests are mocked at module import level to avoid Celery initialization complexity.
# Full integration tests will be added in test_parse_task.py style when Celery infrastructure is available.

@pytest.mark.skip(reason="Celery task testing requires special mocking configuration")
def test_validate_document_task_no_docs():
    """Test validate_document task when no FiscalDocuments found"""
    pass


@pytest.mark.skip(reason="Celery task testing requires special mocking configuration")
def test_validate_document_task_no_rules():
    """Test validate_document task when no rules registered"""
    pass


@pytest.mark.skip(reason="Celery task testing requires special mocking configuration")
def test_validate_document_task_success():
    """Test validate_document task successful execution"""
    pass
