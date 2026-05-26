"""
FiscalAI Configuration Settings
"""
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings
from typing import List

_DEFAULT_SECRET_KEY = "fiscal-ai-development-key-change-in-production"

class Settings(BaseSettings):
    """Application settings from environment variables"""

    # API Configuration
    API_TITLE: str = "FiscalAI"
    API_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://fiscalai_user:fiscalai_password_dev@localhost:5432/fiscalai_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600

    # MinIO / S3
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin_password_dev"
    MINIO_BUCKET_NAME: str = "fiscalai-documents"
    MINIO_USE_SSL: bool = False

    @field_validator("MINIO_ENDPOINT", mode="before")
    @classmethod
    def strip_minio_scheme(cls, v: str) -> str:
        import warnings
        for prefix in ("https://", "http://"):
            if v.startswith(prefix):
                stripped = v[len(prefix):]
                warnings.warn(
                    f"MINIO_ENDPOINT contained URL scheme '{prefix}' — stripped to '{stripped}'. "
                    "MinIO SDK expects host:port or hostname only.",
                    stacklevel=2,
                )
                return stripped
        return v

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_TASK_TIME_LIMIT: int = 3600
    CELERY_TASK_SOFT_TIME_LIMIT: int = 3000

    # CORS — never use "*" with allow_credentials=True in production
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Security
    SECRET_KEY: str = _DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Branding (white-label / adriner.fr)
    BRAND_NAME: str = "FiscalAI"
    BRAND_EXPERT_NAME: str = ""
    BRAND_EXPERT_TITLE: str = ""
    BRAND_WHATSAPP: str = ""
    BRAND_LOGO_URL: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_strength(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @model_validator(mode="after")
    def warn_insecure_defaults(self) -> "Settings":
        import warnings
        if not self.DEBUG and self.SECRET_KEY == _DEFAULT_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY must be changed from the default value in production (DEBUG=False)"
            )
        if not self.DEBUG and self.CORS_ORIGINS == "*":
            raise ValueError(
                "CORS_ORIGINS cannot be '*' in production (DEBUG=False). "
                "Set it to your frontend domain(s)."
            )
        if self.DEBUG and self.SECRET_KEY == _DEFAULT_SECRET_KEY:
            warnings.warn(
                "Using default SECRET_KEY in development mode. "
                "Set SECRET_KEY in .env before deploying.",
                stacklevel=2,
            )
        return self

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
