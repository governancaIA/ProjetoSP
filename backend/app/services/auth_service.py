"""
Authentication service for user management and token handling
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.user import User, RefreshToken
from app.models.tenant_config import TenantConfig
from app.core.validators import validate_cnpj
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_token,
)
from app.core.config import settings
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, OnboardingRequest


class AuthService:
    """Service for authentication operations"""

    @staticmethod
    def register(db: Session, request: RegisterRequest) -> User:
        """
        Register a new user

        Args:
            db: Database session
            request: Registration request with email, password, full_name, tenant_id

        Returns:
            Created User object

        Raises:
            ValueError: If email already exists
        """
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise ValueError("Email já cadastrado")

        # Create new user
        user = User(
            email=request.email,
            hashed_password=get_password_hash(request.password),
            full_name=request.full_name,
            tenant_id=request.tenant_id,
            is_active=True,
            is_admin=False,
        )

        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Failed to register user: {str(e)}")

        # Create isolated PostgreSQL schema for this tenant (atomic with user creation)
        try:
            from app.core.database import create_tenant_schema
            create_tenant_schema(request.tenant_id)
        except Exception as e:
            # Schema creation failure rolls back the user — keep DB consistent
            db.delete(user)
            db.commit()
            raise ValueError(f"Failed to initialize tenant workspace: {str(e)}")

        return user

    @staticmethod
    def authenticate(db: Session, email: str, password: str) -> User | None:
        """
        Authenticate a user by email and password

        Args:
            db: Database session
            email: User email
            password: Plain password

        Returns:
            User object if authentication succeeds, None otherwise
        """
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        if not user.is_active:
            return None

        return user

    @staticmethod
    def login(db: Session, request: LoginRequest) -> TokenResponse | None:
        """
        Login a user and return tokens

        Args:
            db: Database session
            request: Login request with email and password

        Returns:
            TokenResponse with access and refresh tokens, or None if auth fails
        """
        user = AuthService.authenticate(db, request.email, request.password)
        if not user:
            return None

        # Create access token
        access_token = create_access_token(user.id, user.tenant_id)

        # Create refresh token
        raw_refresh_token, refresh_token_hash = create_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        refresh_token_obj = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
            revoked=False,
        )

        try:
            db.add(refresh_token_obj)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Failed to create refresh token: {str(e)}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        )

    @staticmethod
    def refresh_access_token(db: Session, raw_refresh_token: str) -> TokenResponse | None:
        """
        Refresh an access token using a refresh token

        Args:
            db: Database session
            raw_refresh_token: Raw refresh token from client

        Returns:
            TokenResponse with new access and refresh tokens, or None if token is invalid
        """
        token_hash = hash_token(raw_refresh_token)

        # Find the refresh token
        refresh_token_obj = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked == False,
            )
            .first()
        )

        if not refresh_token_obj:
            return None

        # Check expiration (handle both timezone-aware and naive datetimes)
        expires_at = refresh_token_obj.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            return None

        # Get user
        user = refresh_token_obj.user
        if not user or not user.is_active:
            return None

        # Create new access token
        access_token = create_access_token(user.id, user.tenant_id)

        # Optionally: create a new refresh token (rotate on each refresh)
        # For MVP, we can reuse the same refresh token or create a new one
        # Let's create a new one for better security
        raw_new_refresh_token, new_refresh_token_hash = create_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Revoke old refresh token and create new one
        refresh_token_obj.revoked = True
        new_refresh_token_obj = RefreshToken(
            user_id=user.id,
            token_hash=new_refresh_token_hash,
            expires_at=expires_at,
            revoked=False,
        )

        try:
            db.add(new_refresh_token_obj)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            return None

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    def complete_onboarding(db: Session, tenant_id: str, request: OnboardingRequest) -> TenantConfig:
        """
        Validate CNPJ and persist TenantConfig for the tenant.
        Idempotent: upserts if onboarding was already completed.

        Raises:
            ValueError: If CNPJ check digits are invalid
        """
        cnpj_digits = "".join(c for c in request.cnpj if c.isdigit())
        if not validate_cnpj(cnpj_digits):
            raise ValueError(f"CNPJ inválido: {request.cnpj}")

        cfg = db.query(TenantConfig).filter_by(tenant_id=tenant_id).first()
        if cfg is None:
            cfg = TenantConfig(tenant_id=tenant_id)
            db.add(cfg)

        cfg.cnpj_principal = cnpj_digits
        cfg.razao_social = request.razao_social
        cfg.uf = request.uf.upper()
        cfg.regime_tributario = request.regime_tributario
        cfg.onboarding_completed = True

        db.commit()
        db.refresh(cfg)
        return cfg

    @staticmethod
    def get_onboarding_status(db: Session, tenant_id: str) -> TenantConfig | None:
        """Return TenantConfig for the tenant, or None if not yet configured."""
        return db.query(TenantConfig).filter_by(tenant_id=tenant_id).first()

    @staticmethod
    def logout(db: Session, raw_refresh_token: str, user_id: int) -> bool:
        """
        Logout a user by revoking their refresh token.
        Verifies the token belongs to user_id to prevent cross-user revocation.
        """
        token_hash = hash_token(raw_refresh_token)

        refresh_token_obj = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.user_id == user_id,
            )
            .first()
        )

        if not refresh_token_obj:
            return False

        refresh_token_obj.revoked = True
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
