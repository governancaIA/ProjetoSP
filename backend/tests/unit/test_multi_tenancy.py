"""
Tests for EPIC 14: Multi-tenancy foundation
  - QueuePool engine configuration (AC3)
  - TenantMiddleware JWT extraction (AC2)
  - CNPJ validation utility (AC4)
  - Onboarding service logic (AC4, AC5)
  - Onboarding schemas validation (AC4)
"""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# AC3: QueuePool
# ---------------------------------------------------------------------------

class TestQueuePool:
    def test_engine_uses_queue_pool(self):
        from sqlalchemy.pool import QueuePool
        from app.core.database import engine
        assert isinstance(engine.pool, QueuePool)

    def test_engine_pool_size(self):
        from app.core.database import engine
        assert engine.pool.size() == 10

    def test_engine_max_overflow(self):
        from app.core.database import engine
        # QueuePool._max_overflow is the configured max_overflow value
        assert engine.pool._max_overflow == 20


# ---------------------------------------------------------------------------
# AC4: CNPJ validation
# ---------------------------------------------------------------------------

class TestValidateCnpj:
    """Unit tests for validate_cnpj() check-digit algorithm."""

    def test_valid_cnpj_raw(self):
        from app.core.validators import validate_cnpj
        # Real CNPJ: Petrobras (public domain)
        assert validate_cnpj("33000167000101") is True

    def test_valid_cnpj_formatted(self):
        from app.core.validators import validate_cnpj
        assert validate_cnpj("33.000.167/0001-01") is True

    def test_invalid_check_digit(self):
        from app.core.validators import validate_cnpj
        assert validate_cnpj("33000167000199") is False

    def test_too_short(self):
        from app.core.validators import validate_cnpj
        assert validate_cnpj("1234567") is False

    def test_too_long(self):
        from app.core.validators import validate_cnpj
        assert validate_cnpj("123456789012345") is False

    def test_all_zeros_invalid(self):
        from app.core.validators import validate_cnpj
        assert validate_cnpj("00000000000000") is False

    def test_all_same_digit_invalid(self):
        from app.core.validators import validate_cnpj
        assert validate_cnpj("11111111111111") is False

    def test_non_digit_chars_filtered(self):
        from app.core.validators import validate_cnpj
        # Letters mixed in → stripped → becomes short → False
        assert validate_cnpj("ABCDEFGHIJKLMN") is False

    def test_empty_string(self):
        from app.core.validators import validate_cnpj
        assert validate_cnpj("") is False


# ---------------------------------------------------------------------------
# AC2: TenantMiddleware JWT extraction helper
# ---------------------------------------------------------------------------

class TestExtractTenantId:
    """Tests for the _extract_tenant_id helper (pure JWT decode, no DB)."""

    def _make_token(self, tenant_id: str) -> str:
        from app.core.security import create_access_token
        return create_access_token(user_id=1, tenant_id=tenant_id)

    def test_valid_bearer_returns_tenant_id(self):
        from app.core.middleware import _extract_tenant_id
        token = self._make_token("org_abc")
        request = MagicMock()
        request.headers = {"Authorization": f"Bearer {token}"}
        assert _extract_tenant_id(request) == "org_abc"

    def test_missing_header_returns_none(self):
        from app.core.middleware import _extract_tenant_id
        request = MagicMock()
        request.headers = {}
        assert _extract_tenant_id(request) is None

    def test_invalid_token_returns_none(self):
        from app.core.middleware import _extract_tenant_id
        request = MagicMock()
        request.headers = {"Authorization": "Bearer invalid.token.here"}
        assert _extract_tenant_id(request) is None

    def test_non_bearer_scheme_returns_none(self):
        from app.core.middleware import _extract_tenant_id
        token = self._make_token("org_abc")
        request = MagicMock()
        request.headers = {"Authorization": f"Basic {token}"}
        assert _extract_tenant_id(request) is None


# ---------------------------------------------------------------------------
# AC4 + AC5: OnboardingRequest schema validation
# ---------------------------------------------------------------------------

class TestOnboardingSchema:
    def test_valid_request(self):
        from app.schemas.auth import OnboardingRequest
        req = OnboardingRequest(
            cnpj="33000167000101",
            razao_social="PETROBRAS SA",
            uf="RJ",
            regime_tributario="lucro_real",
        )
        assert req.regime_tributario == "lucro_real"

    def test_invalid_regime_raises(self):
        from app.schemas.auth import OnboardingRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            OnboardingRequest(
                cnpj="33000167000101",
                razao_social="ACME",
                uf="SP",
                regime_tributario="regime_invalido",
            )

    def test_all_valid_regimes_accepted(self):
        from app.schemas.auth import OnboardingRequest
        for regime in ("lucro_real", "lucro_presumido", "simples_nacional"):
            req = OnboardingRequest(
                cnpj="33000167000101",
                razao_social="TEST",
                uf="SP",
                regime_tributario=regime,
            )
            assert req.regime_tributario == regime


# ---------------------------------------------------------------------------
# AC4 + AC5: AuthService.complete_onboarding / get_onboarding_status
# ---------------------------------------------------------------------------

class TestAuthServiceOnboarding:
    """Tests for the onboarding service methods using mocked DB sessions."""

    _VALID_CNPJ = "33000167000101"

    def _make_request(self, cnpj=None, regime="lucro_real"):
        from app.schemas.auth import OnboardingRequest
        return OnboardingRequest(
            cnpj=cnpj or self._VALID_CNPJ,
            razao_social="ACME LTDA",
            uf="SP",
            regime_tributario=regime,
        )

    def test_complete_onboarding_creates_config(self):
        from app.services.auth_service import AuthService
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None

        cfg_mock = MagicMock()
        cfg_mock.onboarding_completed = "1"
        cfg_mock.regime_tributario = "lucro_real"

        def refresh_side_effect(obj):
            obj.onboarding_completed = "1"
            obj.regime_tributario = "lucro_real"

        db.refresh.side_effect = refresh_side_effect

        result = AuthService.complete_onboarding(db, "tenant_abc", self._make_request())
        db.add.assert_called_once()
        db.commit.assert_called_once()
        assert result.onboarding_completed == "1"

    def test_complete_onboarding_invalid_cnpj_raises(self):
        from app.services.auth_service import AuthService
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        with pytest.raises(ValueError, match="CNPJ inválido"):
            AuthService.complete_onboarding(db, "tenant_abc", self._make_request(cnpj="00000000000000"))

    def test_complete_onboarding_upserts_existing(self):
        from app.services.auth_service import AuthService
        from app.models.tenant_config import TenantConfig
        db = MagicMock()
        existing = TenantConfig(tenant_id="tenant_abc", onboarding_completed="0")
        db.query.return_value.filter_by.return_value.first.return_value = existing

        def refresh_side_effect(obj):
            obj.onboarding_completed = "1"
            obj.regime_tributario = "lucro_presumido"

        db.refresh.side_effect = refresh_side_effect

        req = self._make_request(regime="lucro_presumido")
        result = AuthService.complete_onboarding(db, "tenant_abc", req)
        # Should NOT call db.add (existing object updated in place)
        db.add.assert_not_called()
        assert result.onboarding_completed == "1"

    def test_get_onboarding_status_none_when_missing(self):
        from app.services.auth_service import AuthService
        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        result = AuthService.get_onboarding_status(db, "tenant_xyz")
        assert result is None

    def test_get_onboarding_status_returns_config(self):
        from app.services.auth_service import AuthService
        from app.models.tenant_config import TenantConfig
        db = MagicMock()
        cfg = TenantConfig(
            tenant_id="tenant_abc",
            onboarding_completed="1",
            regime_tributario="simples_nacional",
        )
        db.query.return_value.filter_by.return_value.first.return_value = cfg
        result = AuthService.get_onboarding_status(db, "tenant_abc")
        assert result is cfg
        assert result.regime_tributario == "simples_nacional"
