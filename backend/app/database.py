"""
Database configuration and session management for EVE Wargames.

Uses SQLAlchemy for ORM and database operations.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from typing import Generator, Dict
from contextlib import contextmanager
import logging
import time

from .config import settings

logger = logging.getLogger(__name__)

# Create database engine with optimized connection pool settings
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_connection_pool_status() -> Dict:
    """
    Get current database connection pool status for monitoring.
    
    Returns:
        dict: Connection pool statistics including size, checked out connections, etc.
    """
    pool = engine.pool
    checked_out = pool.checkedout()
    total_capacity = pool.size() + pool.overflow()
    utilization = (checked_out / total_capacity * 100) if total_capacity > 0 else 0
    
    return {
        "pool_size": pool.size(),
        "checked_out_connections": checked_out,
        "overflow_connections": pool.overflow(),
        "checked_in_connections": pool.checkedin(),
        "total_connections": total_capacity,
        "available_connections": total_capacity - checked_out,
        "utilization_percent": round(utilization, 2),
        "health_status": _get_pool_health_status(utilization),
        "max_overflow": getattr(pool, '_max_overflow', 'unknown'),
        "pool_timeout": getattr(pool, '_timeout', 'unknown'),
        "pool_recycle": getattr(pool, '_recycle', 'unknown'),
        "configuration": {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_recycle": settings.DB_POOL_RECYCLE
        }
    }


def _get_pool_health_status(utilization: float) -> str:
    """Determine pool health status based on utilization."""
    if utilization < 50:
        return "healthy"
    elif utilization < 75:
        return "warning"
    elif utilization < 90:
        return "critical"
    else:
        return "emergency"


def get_detailed_connection_info() -> Dict:
    """
    Get detailed connection information for debugging.
    
    Returns:
        Dict: Detailed connection pool information
    """
    pool = engine.pool
    status = get_connection_pool_status()
    
    return {
        **status,
        "pool_class": pool.__class__.__name__,
        "invalid_connections": getattr(pool, '_invalidated', 0),
        "connection_creation_failures": getattr(pool, '_creation_failures', 0)
    }


def log_connection_pool_status() -> None:
    """Log current connection pool status for debugging."""
    try:
        status = get_connection_pool_status()
        logger.info(f"Connection pool status: {status}")
    except Exception as e:
        logger.error(f"Failed to get connection pool status: {e}")


# Query performance monitoring
@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries for performance monitoring."""
    context._query_start_time = time.time()


@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries for performance monitoring."""
    total = time.time() - context._query_start_time
    if total > 1.0:  # Log queries taking more than 1 second
        logger.warning(f"Slow query detected: {total:.2f}s - {statement[:200]}...")
    elif total > 5.0:  # Log very slow queries as errors
        logger.error(f"Very slow query detected: {total:.2f}s - {statement[:200]}...")


@contextmanager
def get_db_with_timing():
    """
    Database session context manager with timing information.
    
    Yields:
        tuple: (Session, timing_info dict)
    """
    start_time = time.time()
    db = SessionLocal()
    timing_info = {"session_created": time.time() - start_time}
    
    try:
        yield db, timing_info
    finally:
        timing_info["session_duration"] = time.time() - start_time
        db.close()
        if timing_info["session_duration"] > 30.0:  # Log long-held sessions
            logger.warning(f"Long-held database session: {timing_info['session_duration']:.2f}s")
