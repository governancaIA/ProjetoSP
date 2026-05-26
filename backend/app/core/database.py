"""
Database configuration and tenant routing
"""
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool

from app.core.config import settings

# Tenant ID must be safe for schema name interpolation (PostgreSQL doesn't support
# parameterized identifiers, so we validate strictly before interpolating).
_TENANT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{3,100}$")

def _validate_tenant_id(tenant_id: str) -> str:
    """Raise ValueError if tenant_id is not safe for schema interpolation."""
    if not _TENANT_ID_RE.match(tenant_id):
        raise ValueError(f"Invalid tenant_id format: {tenant_id!r}")
    return tenant_id

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def set_tenant_schema(session: Session, tenant_id: str) -> None:
    """
    Set the current schema for a session (multi-tenancy support).
    tenant_id is validated against a strict regex before interpolation.
    """
    _validate_tenant_id(tenant_id)
    schema_name = f"tenant_{tenant_id}"
    session.execute(text(f'SET search_path TO "{schema_name}", public'))
    session.commit()

def create_tenant_schema(tenant_id: str) -> None:
    """
    Create a new schema for a tenant.
    tenant_id is validated against a strict regex before interpolation.
    """
    _validate_tenant_id(tenant_id)
    schema_name = f"tenant_{tenant_id}"
    with engine.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        conn.commit()
    Base.metadata.create_all(bind=engine)
