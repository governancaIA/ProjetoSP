"""
Prometheus metrics registry for FiscalAI.
Imported lazily by TenantMiddleware to avoid circular imports at startup.
"""
from prometheus_client import Counter, Histogram, Info

HTTP_REQUESTS_TOTAL = Counter(
    "fiscalai_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "fiscalai_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

APP_INFO = Info("fiscalai_app", "FiscalAI application metadata")
APP_INFO.info({"version": "0.1.0", "environment": "production"})
