"""
EVE Wargames FastAPI Application

Main entry point for the EVE Online Faction Warfare tracking application.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from app.config import settings
from app.api import faction_warfare, systems, kills
from app.database import engine, Base
from app.services.esi_client import esi_client

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="EVE Wargames API",
    description="API for tracking EVE Online Faction Warfare data in the Minmatar/Amarr warzone",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(
    faction_warfare.router,
    prefix="/api/v1/faction-warfare",
    tags=["Faction Warfare"]
)

app.include_router(
    systems.router,
    prefix="/api/v1/systems",
    tags=["Systems"]
)

app.include_router(
    kills.router,
    prefix="/api/v1/kills",
    tags=["Kills"]
)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "EVE Wargames API",
        "version": "1.0.0",
        "description": "API for tracking EVE Online Faction Warfare data",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "eve-wargames-api"}

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    await esi_client.close()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )
