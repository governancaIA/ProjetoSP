"""
FastAPI dependencies for authentication and database
"""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, _validate_tenant_id
from app.core.security import verify_access_token
from app.models.user import User

security = HTTPBearer()


def get_db(request: Request):
    """
    Yield a DB session with search_path set to the current tenant's schema.
    Reads tenant_id from request.state (populated by TenantMiddleware).
    Falls back to public schema for unauthenticated/public endpoints.
    """
    db = SessionLocal()
    try:
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            try:
                _validate_tenant_id(tenant_id)
                schema_name = f"tenant_{tenant_id}"
                db.execute(text(f'SET search_path TO "{schema_name}", public'))
            except ValueError:
                pass  # invalid tenant_id format — downstream auth will reject
        yield db
    finally:
        db.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer credentials
        db: Database session (with search_path already set by get_db)

    Returns:
        Current User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    payload = verify_access_token(token)

    user_id = int(payload.get("sub"))
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
