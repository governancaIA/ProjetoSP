"""
Structured JSON logging with PII masking.
Call configure_logging() once at application startup, before any other import
that creates a logger. All child loggers inherit the root handler automatically —
no changes required in existing logging.getLogger(__name__) call sites.

LGPD Art. 46 — masked fields:
  - 44-digit chave de acesso (NF-e / CT-e)
  - 14-digit CNPJ (bare or formatted XX.XXX.XXX/XXXX-XX)
  - 11-digit CPF  (bare or formatted XXX.XXX.XXX-XX)
"""
import re
import logging
import contextvars
from typing import Optional

from pythonjsonlogger import jsonlogger

# 44-digit NF-e / CT-e access key
_CHAVE_ACESSO_RE = re.compile(r"\b\d{44}\b")
# 14-digit CNPJ — bare (12345678000195) or formatted (12.345.678/0001-95)
_CNPJ_RE = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}[/\\]?\d{4}-?\d{2}\b")
# 11-digit CPF — bare (12345678901) or formatted (123.456.789-01)
_CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")

_tenant_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "log_tenant_id", default=None
)
_request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "log_request_id", default=None
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

    @staticmethod
    def set_request_id(request_id: Optional[str]) -> contextvars.Token:
        return _request_id_var.set(request_id)

    @staticmethod
    def reset_request_id(token: contextvars.Token) -> None:
        _request_id_var.reset(token)

    @staticmethod
    def get_request_id() -> Optional[str]:
        return _request_id_var.get()


class _ContextFilter(logging.Filter):
    """Injects tenant_id and request_id from ContextVars into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.tenant_id = _tenant_id_var.get()
        record.request_id = _request_id_var.get()
        return True


def _mask_pii(text: str) -> str:
    """Apply all LGPD masking patterns to a string."""
    text = _CHAVE_ACESSO_RE.sub("***CHAVE***", text)
    text = _CNPJ_RE.sub("***CNPJ***", text)
    text = _CPF_RE.sub("***CPF***", text)
    return text


class _JsonMaskingFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that masks PII (chave de acesso, CNPJ, CPF) per LGPD Art. 46."""

    def format(self, record: logging.LogRecord) -> str:
        return _mask_pii(super().format(record))


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
    handler.addFilter(_ContextFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))
