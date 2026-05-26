"""
Authentication endpoints (register, login, refresh, logout, me)
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshRequest,
    UserOut,
    OnboardingRequest,
    OnboardingStatusResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(request: Request, register_request: RegisterRequest, db: Session = Depends(get_db)) -> User:
    """
    Register a new user

    Args:
        request: Registration request with email, password, full_name, tenant_id
        db: Database session

    Returns:
        Created user (without password)

    Raises:
        HTTPException: If email already exists
    """
    try:
        user = AuthService.register(db, register_request)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, login_request: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Login user with email and password

    Args:
        request: Login request with email and password
        db: Database session

    Returns:
        Token response with access_token and refresh_token

    Raises:
        HTTPException: If credentials are invalid
    """
    token_response = AuthService.login(db, login_request)
    if not token_response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return token_response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """
    Refresh access token using refresh token

    Args:
        request: Refresh request with refresh_token
        db: Database session

    Returns:
        Token response with new access_token and refresh_token

    Raises:
        HTTPException: If refresh token is invalid or expired
    """
    token_response = AuthService.refresh_access_token(db, request.refresh_token)
    if not token_response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return token_response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: RefreshRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Logout user by revoking refresh token

    Args:
        request: Refresh token to revoke
        current_user: Current authenticated user (from Bearer token)
        db: Database session

    Raises:
        HTTPException: If logout fails
    """
    success = AuthService.logout(db, request.refresh_token, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to logout",
        )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current authenticated user

    Args:
        current_user: Current authenticated user (from Bearer token)

    Returns:
        Current user (without password)
    """
    return current_user


@router.post("/onboarding", response_model=OnboardingStatusResponse, status_code=status.HTTP_200_OK)
async def complete_onboarding(
    request: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnboardingStatusResponse:
    """
    Complete tenant onboarding: validate CNPJ and save fiscal configuration.
    Idempotent — can be called again to update configuration.
    """
    try:
        cfg = AuthService.complete_onboarding(db, current_user.tenant_id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return OnboardingStatusResponse(
        completed=bool(cfg.onboarding_completed),
        regime_tributario=cfg.regime_tributario,
    )


@router.get("/onboarding/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OnboardingStatusResponse:
    """Return onboarding completion status for the current tenant."""
    cfg = AuthService.get_onboarding_status(db, current_user.tenant_id)
    if cfg is None:
        return OnboardingStatusResponse(completed=False, regime_tributario=None)
    return OnboardingStatusResponse(
        completed=bool(cfg.onboarding_completed),
        regime_tributario=cfg.regime_tributario,
    )
