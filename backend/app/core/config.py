"""
FiscalAI Configuration Settings
"""
from pydantic_settings import BaseSettings
from typing import List

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
    REDIS_CACHE_TTL: int = 3600  # 1 hour

    # MinIO / S3
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin_password_dev"
    MINIO_BUCKET_NAME: str = "fiscalai-documents"
    MINIO_USE_SSL: bool = False

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    CELERY_TASK_TIME_LIMIT: int = 3600  # 1 hour
    CELERY_TASK_SOFT_TIME_LIMIT: int = 3000  # 50 minutes

    # CORS
    CORS_ORIGINS: str = "*"

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # Security
    SECRET_KEY: str = "fiscal-ai-development-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
