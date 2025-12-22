"""
Database configuration and session management for EVE Wargames.

Uses SQLAlchemy for ORM and database operations.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Dict
import logging

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
    return {
        "pool_size": pool.size(),
        "checked_out_connections": pool.checkedout(),
        "overflow_connections": pool.overflow(),
        "checked_in_connections": pool.checkedin(),
        "total_connections": pool.size() + pool.overflow(),
        "max_overflow": getattr(pool, '_max_overflow', 'unknown'),
        "pool_timeout": getattr(pool, '_timeout', 'unknown'),
        "pool_recycle": getattr(pool, '_recycle', 'unknown')
    }


def log_connection_pool_status() -> None:
    """Log current connection pool status for debugging."""
    try:
        status = get_connection_pool_status()
        logger.info(f"Connection pool status: {status}")
    except Exception as e:
        logger.error(f"Failed to get connection pool status: {e}")
