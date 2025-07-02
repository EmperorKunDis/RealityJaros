from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import logging

from src.config.settings import settings
from src.config.database import create_tables
from src.config.logging import setup_logging

# Import models to ensure they are registered with SQLAlchemy
from src.models import *

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management
    Handles startup and shutdown procedures
    """
    # Startup
    logger.info("Starting AI Email Assistant application...")
    await create_tables()
    logger.info("Database tables initialized")
    
    # Initialize vector databases
    try:
        from src.services.vector_db_manager import VectorDatabaseManager
        vector_manager = VectorDatabaseManager()
        await vector_manager.initialize_collections()
        logger.info("Vector databases initialized")
    except Exception as e:
        logger.warning(f"Vector database initialization failed: {e}. Continuing without vector services.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Email Assistant application...")

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Advanced AI-powered email assistant with RAG capabilities",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Security middleware
security = HTTPBearer()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.example.com"]
)

# GDPR compliance middleware
from src.middleware.gdpr_audit import GDPRComplianceMiddleware
app.add_middleware(GDPRComplianceMiddleware)

# Include API routers
from src.api.routes import auth, emails, clients, responses, analysis, vectors, tasks, setup_wizard, monitoring, ultimate_prompts, auto_send, gdpr_compliance, google_services

app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(emails.router, prefix="/api/v1/emails", tags=["emails"])
app.include_router(clients.router, prefix="/api/v1/clients", tags=["clients"])
app.include_router(responses.router, prefix="/api/v1/responses", tags=["responses"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(vectors.router, prefix="/api/v1/vectors", tags=["vectors"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["background_tasks"])
app.include_router(setup_wizard.router, prefix="/api/v1/setup-wizard", tags=["setup_wizard"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])
app.include_router(ultimate_prompts.router, prefix="/api/v1/prompts", tags=["ultimate_prompts"])
app.include_router(auto_send.router, prefix="/api/v1/auto-send", tags=["auto_send"])
app.include_router(gdpr_compliance.router, prefix="/api/v1/gdpr", tags=["gdpr_compliance"])
app.include_router(google_services.router, prefix="/api/v1/google", tags=["google_services"])

@app.get("/")
async def root():
    """Root endpoint with application information"""
    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "status": "operational",
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": settings.app_version
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )