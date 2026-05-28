"""
Tenant-aware middleware: extracts tenant_id from JWT and stores in request.state.
Also handles:
  - X-Request-ID propagation (generated if absent)
  - Prometheus HTTP metrics (counter + latency histogram)
  - Async audit log writes for mutating requests (POST/PUT/PATCH/DELETE)
"""
import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from jose import jwt, JWTError

from app.core.config import settings
from app.core.logging_config import LogContext

logger = logging.getLogger(__name__)

# Paths that do not require tenant context (public / pre-auth)
_SKIP_PATHS = frozenset({
    "/health",
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/metrics",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
})

# Only audit-log mutating verbs (reads are too noisy and less relevant for LGPD)
_AUDIT_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Per-request middleware that:
    1. Decodes JWT → tenant_id + user_id stored in request.state
    2. Assigns/propagates X-Request-ID
    3. Records Prometheus HTTP metrics
    4. Writes audit log entry (background) for mutating requests
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()

        # ── Request-ID ────────────────────────────────────────────────
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # ── Tenant / user from JWT ────────────────────────────────────
        tenant_id = None
        user_id = None
        if request.url.path not in _SKIP_PATHS:
            tenant_id, user_id = _extract_jwt_claims(request)

        request.state.tenant_id = tenant_id

        # ── Log context vars ──────────────────────────────────────────
        tok_tenant = LogContext.set_tenant(tenant_id)
        tok_rid = LogContext.set_request_id(request_id)

        try:
            response = await call_next(request)
        except Exception:
            raise
        finally:
            LogContext.reset_tenant(tok_tenant)
            LogContext.reset_request_id(tok_rid)

        # ── Prometheus metrics (best-effort) ──────────────────────────
        duration_ms = int((time.perf_counter() - start) * 1000)
        try:
            from app.core.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION
            label_path = _normalize_path(request.url.path)
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                path=label_path,
                status=str(response.status_code),
            ).inc()
            HTTP_REQUEST_DURATION.labels(
                method=request.method,
                path=label_path,
            ).observe(duration_ms / 1000)
        except Exception:
            pass  # never let metrics break a request

        # ── Audit log (fire-and-forget via background task) ───────────
        if request.method in _AUDIT_METHODS and tenant_id:
            try:
                from starlette.background import BackgroundTask
                # Attach background task to response so it runs after response is sent
                audit_task = BackgroundTask(
                    _write_audit_log,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    ip_address=_get_client_ip(request),
                )
                # Merge with any existing background tasks on the response
                if response.background is None:
                    response.background = audit_task
                else:
                    from starlette.background import BackgroundTasks
                    tasks = BackgroundTasks()
                    tasks.add_task(
                        _write_audit_log,
                        tenant_id=tenant_id,
                        user_id=user_id,
                        request_id=request_id,
                        method=request.method,
                        path=request.url.path,
                        status_code=response.status_code,
                        duration_ms=duration_ms,
                        ip_address=_get_client_ip(request),
                    )
                    response.background = tasks
            except Exception as exc:
                logger.debug("Audit log enqueue failed: %s", exc)

        response.headers["X-Request-ID"] = request_id
        return response


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_jwt_claims(request: Request) -> tuple[str | None, int | None]:
    """Return (tenant_id, user_id) from Bearer JWT. Pure in-process, no DB."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, None
    token = auth_header[len("Bearer "):]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("tenant_id"), payload.get("user_id")
    except JWTError:
        return None, None


def _extract_tenant_id(request: Request) -> str | None:
    """Backwards-compatible alias — returns only tenant_id."""
    tenant_id, _ = _extract_jwt_claims(request)
    return tenant_id


def _get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


# Collapse path params to reduce cardinality in Prometheus labels
_PATH_PARAM_RE = __import__("re").compile(r"/\d+")

def _normalize_path(path: str) -> str:
    return _PATH_PARAM_RE.sub("/{id}", path)


def _write_audit_log(
    *,
    tenant_id: str,
    user_id: int | None,
    request_id: str,
    method: str,
    path: str,
    status_code: int,
    duration_ms: int,
    ip_address: str | None,
) -> None:
    """Write one audit log row synchronously (called from Starlette BackgroundTask)."""
    try:
        from app.core.database import SessionLocal, set_tenant_schema
        from app.models.audit_log import AuditLog

        db = SessionLocal()
        try:
            # Audit logs live in the public schema (not tenant schema) so they
            # can be queried by admin without knowing the tenant upfront.
            entry = AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                request_id=request_id,
                ip_address=ip_address,
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            db.add(entry)
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Audit log write failed: %s", exc)
