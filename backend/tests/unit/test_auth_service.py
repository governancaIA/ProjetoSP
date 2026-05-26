"""
Tests for authentication service
"""
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.database import Base
from app.models.user import User, RefreshToken
from app.services.auth_service import AuthService
from app.schemas.auth import RegisterRequest, LoginRequest
from app.core.security import hash_token


# SQLite in-memory database for testing
@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


class TestAuthServiceRegister:
    """User registration tests"""

    def test_register_new_user(self, test_db: Session):
        """Test successful user registration"""
        request = RegisterRequest(
            email="test@example.com",
            password="securepassword123",
            full_name="Test User",
            tenant_id="org_001",
        )
        user = AuthService.register(test_db, request)
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.tenant_id == "org_001"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.hashed_password != "securepassword123"  # Password should be hashed

    def test_register_duplicate_email(self, test_db: Session):
        """Test registration fails with duplicate email"""
        request1 = RegisterRequest(
            email="test@example.com",
            password="password123",
            full_name="User 1",
            tenant_id="org_001",
        )
        AuthService.register(test_db, request1)

        request2 = RegisterRequest(
            email="test@example.com",
            password="different_password",
            full_name="User 2",
            tenant_id="org_002",
        )
        with pytest.raises(ValueError, match="already registered"):
            AuthService.register(test_db, request2)

    def test_register_multiple_users_same_tenant(self, test_db: Session):
        """Test registering multiple users in the same tenant"""
        for i in range(3):
            request = RegisterRequest(
                email=f"user{i}@example.com",
                password="password123",
                full_name=f"User {i}",
                tenant_id="org_001",
            )
            user = AuthService.register(test_db, request)
            assert user.email == f"user{i}@example.com"


class TestAuthServiceAuthenticate:
    """User authentication tests"""

    @pytest.fixture
    def test_user(self, test_db: Session):
        """Create a test user"""
        request = RegisterRequest(
            email="test@example.com",
            password="securepassword123",
            full_name="Test User",
            tenant_id="org_001",
        )
        return AuthService.register(test_db, request)

    def test_authenticate_valid_credentials(self, test_db: Session, test_user: User):
        """Test authentication with valid credentials"""
        user = AuthService.authenticate(test_db, "test@example.com", "securepassword123")
        assert user is not None
        assert user.email == "test@example.com"

    def test_authenticate_invalid_password(self, test_db: Session, test_user: User):
        """Test authentication with invalid password"""
        user = AuthService.authenticate(test_db, "test@example.com", "wrongpassword")
        assert user is None

    def test_authenticate_nonexistent_user(self, test_db: Session):
        """Test authentication with non-existent email"""
        user = AuthService.authenticate(test_db, "nonexistent@example.com", "password")
        assert user is None

    def test_authenticate_inactive_user(self, test_db: Session, test_user: User):
        """Test authentication fails for inactive users"""
        test_user.is_active = False
        test_db.commit()
        user = AuthService.authenticate(test_db, "test@example.com", "securepassword123")
        assert user is None


class TestAuthServiceLogin:
    """Login endpoint tests"""

    @pytest.fixture
    def test_user(self, test_db: Session):
        """Create a test user"""
        request = RegisterRequest(
            email="test@example.com",
            password="securepassword123",
            full_name="Test User",
            tenant_id="org_001",
        )
        return AuthService.register(test_db, request)

    def test_login_success(self, test_db: Session, test_user: User):
        """Test successful login"""
        request = LoginRequest(email="test@example.com", password="securepassword123")
        token_response = AuthService.login(test_db, request)
        assert token_response is not None
        assert token_response.access_token
        assert token_response.refresh_token
        assert token_response.token_type == "bearer"
        assert token_response.expires_in > 0

    def test_login_invalid_password(self, test_db: Session, test_user: User):
        """Test login fails with invalid password"""
        request = LoginRequest(email="test@example.com", password="wrongpassword")
        token_response = AuthService.login(test_db, request)
        assert token_response is None

    def test_login_creates_refresh_token(self, test_db: Session, test_user: User):
        """Test that login creates a refresh token in database"""
        request = LoginRequest(email="test@example.com", password="securepassword123")
        token_response = AuthService.login(test_db, request)
        assert token_response is not None

        # Verify refresh token was created
        refresh_tokens = test_db.query(RefreshToken).filter_by(user_id=test_user.id).all()
        assert len(refresh_tokens) == 1
        assert refresh_tokens[0].revoked is False


class TestAuthServiceRefreshToken:
    """Refresh token tests"""

    @pytest.fixture
    def authenticated_user(self, test_db: Session):
        """Create and login a test user"""
        register_request = RegisterRequest(
            email="test@example.com",
            password="securepassword123",
            full_name="Test User",
            tenant_id="org_001",
        )
        user = AuthService.register(test_db, register_request)

        login_request = LoginRequest(
            email="test@example.com",
            password="securepassword123",
        )
        token_response = AuthService.login(test_db, login_request)
        return user, token_response.refresh_token

    def test_refresh_access_token_success(self, test_db: Session, authenticated_user):
        """Test successful token refresh"""
        user, refresh_token = authenticated_user
        new_token_response = AuthService.refresh_access_token(test_db, refresh_token)
        assert new_token_response is not None
        assert new_token_response.access_token
        assert new_token_response.refresh_token
        assert new_token_response.token_type == "bearer"

    def test_refresh_with_invalid_token(self, test_db: Session):
        """Test refresh fails with invalid token"""
        new_token_response = AuthService.refresh_access_token(test_db, "invalid_token")
        assert new_token_response is None

    def test_refresh_with_revoked_token(self, test_db: Session, authenticated_user):
        """Test refresh fails with revoked refresh token"""
        user, refresh_token = authenticated_user

        # Revoke the refresh token manually
        token_hash = hash_token(refresh_token)
        refresh_token_obj = test_db.query(RefreshToken).filter_by(token_hash=token_hash).first()
        refresh_token_obj.revoked = True
        test_db.commit()

        # Attempt to refresh should fail
        new_token_response = AuthService.refresh_access_token(test_db, refresh_token)
        assert new_token_response is None

    def test_refresh_with_expired_token(self, test_db: Session, authenticated_user):
        """Test refresh fails with expired refresh token"""
        user, refresh_token = authenticated_user

        # Expire the refresh token manually
        token_hash = hash_token(refresh_token)
        refresh_token_obj = test_db.query(RefreshToken).filter_by(token_hash=token_hash).first()
        refresh_token_obj.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        test_db.commit()

        # Attempt to refresh should fail
        new_token_response = AuthService.refresh_access_token(test_db, refresh_token)
        assert new_token_response is None

    def test_refresh_rotates_token(self, test_db: Session, authenticated_user):
        """Test that refresh creates a new token (rotation)"""
        user, refresh_token = authenticated_user
        new_token_response = AuthService.refresh_access_token(test_db, refresh_token)

        # Old token should be revoked
        old_token_hash = hash_token(refresh_token)
        old_token_obj = test_db.query(RefreshToken).filter_by(token_hash=old_token_hash).first()
        assert old_token_obj.revoked is True

        # New token should exist and not be revoked
        new_token_hash = hash_token(new_token_response.refresh_token)
        new_token_obj = test_db.query(RefreshToken).filter_by(token_hash=new_token_hash).first()
        assert new_token_obj.revoked is False


class TestAuthServiceLogout:
    """Logout endpoint tests"""

    @pytest.fixture
    def authenticated_user(self, test_db: Session):
        """Create and login a test user"""
        register_request = RegisterRequest(
            email="test@example.com",
            password="securepassword123",
            full_name="Test User",
            tenant_id="org_001",
        )
        user = AuthService.register(test_db, register_request)

        login_request = LoginRequest(
            email="test@example.com",
            password="securepassword123",
        )
        token_response = AuthService.login(test_db, login_request)
        return user, token_response.refresh_token

    def test_logout_success(self, test_db: Session, authenticated_user):
        """Test successful logout"""
        user, refresh_token = authenticated_user
        success = AuthService.logout(test_db, refresh_token, user.id)
        assert success is True

        # Verify token is revoked
        token_hash = hash_token(refresh_token)
        refresh_token_obj = test_db.query(RefreshToken).filter_by(token_hash=token_hash).first()
        assert refresh_token_obj.revoked is True

    def test_logout_invalid_token(self, test_db: Session):
        """Test logout fails with invalid token"""
        success = AuthService.logout(test_db, "invalid_token", 999)
        assert success is False

    def test_logout_already_revoked_token(self, test_db: Session, authenticated_user):
        """Test logout of already revoked token"""
        user, refresh_token = authenticated_user
        # First logout
        AuthService.logout(test_db, refresh_token, user.id)
        # Second logout should still succeed (idempotent)
        success = AuthService.logout(test_db, refresh_token, user.id)
        assert success is True
