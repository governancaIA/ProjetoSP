"""
FiscalAI - FastAPI Application Entry Point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api import uploads, documents, validation, auth, jobs, reports

# Global rate limiter — keyed by client IP
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation
    if not settings.DEBUG and settings.SECRET_KEY == "fiscal-ai-development-key-change-in-production":
        raise RuntimeError("SECRET_KEY must be changed from default in production")

    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    yield
    print("🛑 Shutting down FiscalAI")


app = FastAPI(
    title=settings.BRAND_NAME or "FiscalAI",
    description="Brazilian Fiscal Document Validation Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiter state + handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS — never allow * with credentials in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Expose limiter for use in route decorators
app.state.limiter = limiter

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(uploads.router, prefix="/api/v1", tags=["uploads"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(validation.router, prefix="/api/v1", tags=["validation"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])


@app.get("/")
async def root():
    return {"message": f"{settings.BRAND_NAME or 'FiscalAI'} API", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    """Real health check — verifies PostgreSQL, Redis, and MinIO connectivity."""
    from sqlalchemy import text
    from app.core.database import SessionLocal
    import redis as redis_lib
    from minio import Minio

    checks: dict = {}
    overall = "healthy"

    # PostgreSQL
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        checks["postgresql"] = "ok"
    except Exception as e:
        checks["postgresql"] = f"error: {e}"
        overall = "degraded"

    # Redis
    try:
        r = redis_lib.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        overall = "degraded"

    # MinIO
    try:
        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
        client.list_buckets()
        checks["minio"] = "ok"
    except Exception as e:
        checks["minio"] = f"error: {e}"
        overall = "degraded"

    status_code = 200 if overall == "healthy" else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
