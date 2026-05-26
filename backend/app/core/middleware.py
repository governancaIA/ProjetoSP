"""
Tenant-aware middleware: extracts tenant_id from JWT and stores in request.state.
The actual SET search_path is executed by get_db() in api/deps.py using this value.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from jose import jwt, JWTError

from app.core.config import settings

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
    Decodes the JWT from the Authorization header and stores the tenant_id
    in request.state.tenant_id for downstream use by get_db().

    Does NOT open a DB session — that is the responsibility of get_db() which
    will call SET search_path on the session it yields to handlers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        tenant_id = None
        if request.url.path not in _SKIP_PATHS:
            tenant_id = _extract_tenant_id(request)

        request.state.tenant_id = tenant_id
        return await call_next(request)


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
