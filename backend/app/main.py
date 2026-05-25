"""
FiscalAI - FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base
from app.api import uploads, documents, validation, auth

# Create database tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    yield
    # Shutdown
    print("🛑 Shutting down FiscalAI")

# Create FastAPI app
app = FastAPI(
    title="FiscalAI",
    description="Brazilian Fiscal Document Validation Platform",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(uploads.router, prefix="/api/v1", tags=["uploads"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(validation.router, prefix="/api/v1", tags=["validation"])

@app.get("/")
async def root():
    return {
        "message": "FiscalAI API",
        "version": "0.1.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "FiscalAI API"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
