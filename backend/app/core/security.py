"""
JWT and password security utilities
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple
import uuid
import hashlib

from jose import jwt, JWTError
import bcrypt
from fastapi import HTTPException, status

from app.core.config import settings


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: int, tenant_id: str, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token

    Args:
        user_id: User ID to encode in token
        tenant_id: Tenant ID to encode in token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    encoded_jwt = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token() -> Tuple[str, str]:
    """
    Create a refresh token and its hash

    Returns:
        Tuple of (raw_token, token_hash) where:
        - raw_token: UUID-based token to send to client
        - token_hash: SHA-256 hash to store in database
    """
    raw_token = str(uuid.uuid4())
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return raw_token, token_hash


def hash_token(raw_token: str) -> str:
    """Hash a raw token using SHA-256"""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def mask_chave_acesso(chave: str) -> str:
    """
    Mask the CNPJ portion of an NF-e/CT-e chave de acesso for LGPD compliance.

    A 44-digit chave de acesso has the CNPJ emitente at positions 6–19 (14 digits).
    This function replaces those digits with '***' before logging.

    Args:
        chave: 44-character chave de acesso string

    Returns:
        Masked string with CNPJ replaced by '***', or original if input is not a
        44-digit string (e.g. None, empty, already-masked).
    """
    if not isinstance(chave, str) or len(chave) != 44 or not chave.isdigit():
        return str(chave) if chave is not None else ""
    return chave[:6] + "***" + chave[20:]


def verify_access_token(token: str) -> Dict:
    """
    Verify and decode a JWT access token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload dict

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")

        if user_id is None or tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id or tenant_id",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
