"""
Health check endpoints for monitoring system status.

Provides endpoints to check database connectivity, connection pool status,
and overall system health.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database import get_db, get_connection_pool_status, engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        dict: Basic health status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "eve_wargames_backend"
    }


@router.get("/database")
async def database_health_check(db: Session = Depends(get_db)):
    """
    Check database connectivity and basic functionality.
    
    Returns:
        dict: Database health status and connection info
    """
    try:
        # Test basic database connectivity
        result = db.execute(text("SELECT 1 as test")).fetchone()
        
        if result and result.test == 1:
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database": "connected",
                "test_query": "passed"
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Database test query failed"
            )
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database health check failed: {str(e)}"
        )


@router.get("/database/pool")
async def database_pool_status():
    """
    Get detailed database connection pool status.
    
    Returns:
        dict: Connection pool statistics and health status
    """
    try:
        pool_status = get_connection_pool_status()
        
        # Calculate pool utilization percentage
        checked_out = pool_status.get("checked_out_connections", 0)
        total_capacity = pool_status.get("total_connections", 1)
        utilization_percent = (checked_out / total_capacity) * 100 if total_capacity > 0 else 0
        
        # Determine health status based on utilization
        if utilization_percent < 70:
            health_status = "healthy"
        elif utilization_percent < 90:
            health_status = "warning"
        else:
            health_status = "critical"
        
        return {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "pool_utilization_percent": round(utilization_percent, 2),
            "pool_stats": pool_status
        }
        
    except Exception as e:
        logger.error(f"Database pool status check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database pool status check failed: {str(e)}"
        )


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check including database and connection pool status.
    
    Returns:
        dict: Complete system health status
    """
    try:
        # Test database connectivity
        db_result = db.execute(text("SELECT 1 as test")).fetchone()
        db_healthy = db_result and db_result.test == 1
        
        # Get connection pool status
        pool_status = get_connection_pool_status()
        checked_out = pool_status.get("checked_out_connections", 0)
        total_capacity = pool_status.get("total_connections", 1)
        utilization_percent = (checked_out / total_capacity) * 100 if total_capacity > 0 else 0
        
        # Determine overall health
        pool_healthy = utilization_percent < 90
        overall_healthy = db_healthy and pool_healthy
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "eve_wargames_backend",
            "components": {
                "database": {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "test_query": "passed" if db_healthy else "failed"
                },
                "connection_pool": {
                    "status": "healthy" if pool_healthy else "critical",
                    "utilization_percent": round(utilization_percent, 2),
                    "stats": pool_status
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(e)}"
        )
