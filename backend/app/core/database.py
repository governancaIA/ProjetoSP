"""
Database configuration and tenant routing
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,  # Disable pooling for better multi-tenant support
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
    Set the current schema for a session (multi-tenancy support)

    Args:
        session: SQLAlchemy session
        tenant_id: Organization/tenant identifier (e.g., "tenant_org_001")
    """
    schema_name = f"tenant_{tenant_id}"
    # Execute SET search_path to switch to tenant schema
    session.execute(text(f"SET search_path TO {schema_name}, public"))
    session.commit()

def create_tenant_schema(tenant_id: str) -> None:
    """
    Create a new schema for a tenant

    Args:
        tenant_id: Organization/tenant identifier
    """
    schema_name = f"tenant_{tenant_id}"
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        # Create all tables in the new schema
        Base.metadata.create_all(bind=engine, schema=schema_name)
        conn.commit()
