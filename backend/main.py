"""
EVE Wargames FastAPI Application

Main entry point for the EVE Online Faction Warfare tracking application.
"""

import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from app.config import settings
from app.api import faction_warfare, systems, kills
from app.database import engine, Base
from app.services.esi_client import esi_client
from app.logging_config import setup_logging, get_app_logger, set_request_id, clear_request_id

# Setup logging first
setup_logging()
logger = get_app_logger(__name__)

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

# Add request logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log requests and responses with timing and request ID tracking."""
    # Set request ID for tracing
    request_id = set_request_id()
    
    # Log request start
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    
    if settings.LOG_REQUEST_DETAILS:
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": client_ip,
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        if settings.LOG_REQUEST_DETAILS:
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_seconds": round(duration, 3),
                    "client_ip": client_ip
                }
            )
        
        return response
        
    except Exception as e:
        # Calculate duration for error case
        duration = time.time() - start_time
        
        # Log error
        logger.error(
            f"Request failed: {request.method} {request.url.path} - {str(e)} ({duration:.3f}s)",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "duration_seconds": round(duration, 3),
                "client_ip": client_ip
            },
            exc_info=True
        )
        
        # Re-raise the exception
        raise
    
    finally:
        # Clear request ID
        clear_request_id()

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

@app.on_event("startup")
async def startup_event():
    """Log application startup."""
    logger.info(
        f"EVE Wargames API starting up - Version 1.0.0",
        extra={
            "version": "1.0.0",
            "debug_mode": settings.DEBUG,
            "log_level": settings.LOG_LEVEL
        }
    )

@app.get("/")
async def root():
    """Root endpoint with API information."""
    logger.debug("Root endpoint accessed")
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
    logger.debug("Health check endpoint accessed")
    return {"status": "healthy", "service": "eve-wargames-api"}

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    logger.info("EVE Wargames API shutting down")
    await esi_client.close()
    logger.info("Application shutdown complete")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )
