"""
Tenant-aware middleware: sets PostgreSQL search_path per authenticated request.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from jose import jwt, JWTError

from app.core.config import settings
from app.core.database import SessionLocal, _validate_tenant_id

# Paths that do not require tenant context (public / pre-auth)
_SKIP_PATHS = frozenset({
    "/health",
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
})


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Decodes the JWT from the Authorization header and sets the PostgreSQL
    search_path to the tenant's schema for every authenticated request.

    Skips unauthenticated/public paths. If the JWT is missing or invalid,
    the middleware passes the request through unchanged — the route's auth
    dependency will reject it with 401 if authentication is required.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        tenant_id = _extract_tenant_id(request)

        if tenant_id is None:
            return await call_next(request)

        # Validate tenant_id format before using it in SQL
        try:
            _validate_tenant_id(tenant_id)
        except ValueError:
            return await call_next(request)

        # Set search_path for this request's DB session via a scoped session
        db = SessionLocal()
        try:
            from sqlalchemy import text
            schema_name = f"tenant_{tenant_id}"
            db.execute(text(f'SET search_path TO "{schema_name}", public'))
            request.state.db = db
            request.state.tenant_id = tenant_id
            response = await call_next(request)
        finally:
            db.close()

        return response


def _extract_tenant_id(request: Request) -> str | None:
    """
    Decode the JWT Bearer token and return the tenant_id claim.
    Returns None if the header is missing, malformed, or the token is invalid.
    Does NOT hit the database — pure in-process decode.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[len("Bearer "):]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("tenant_id")
    except JWTError:
        return None
