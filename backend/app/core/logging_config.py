"""
Structured JSON logging with PII masking.
Call configure_logging() once at application startup, before any other import
that creates a logger. All child loggers inherit the root handler automatically —
no changes required in existing logging.getLogger(__name__) call sites.
"""
import re
import logging
import contextvars
from typing import Optional

from pythonjsonlogger import jsonlogger

# Matches a 44-digit NF-e / CT-e chave de acesso anywhere in a log message
_CHAVE_ACESSO_RE = re.compile(r"\b\d{44}\b")

_tenant_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "log_tenant_id", default=None
)


class LogContext:
    """Thread/async-safe context for per-request log fields."""

    @staticmethod
    def set_tenant(tenant_id: Optional[str]) -> contextvars.Token:
        return _tenant_id_var.set(tenant_id)

    @staticmethod
    def reset_tenant(token: contextvars.Token) -> None:
        _tenant_id_var.reset(token)

    @staticmethod
    def get_tenant() -> Optional[str]:
        return _tenant_id_var.get()


class _TenantContextFilter(logging.Filter):
    """Injects tenant_id from ContextVar into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.tenant_id = _tenant_id_var.get()
        return True


class _JsonMaskingFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that masks 44-digit chave de acesso in all fields."""

    def format(self, record: logging.LogRecord) -> str:
        json_str = super().format(record)
        return _CHAVE_ACESSO_RE.sub("****MASKED****", json_str)


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure the root logger with JSON output and PII masking.

    Zero changes required in existing code — Python logging propagation
    means all child loggers inherit the root handler's formatter.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(
        _JsonMaskingFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        )
    )
    handler.addFilter(_TenantContextFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))
