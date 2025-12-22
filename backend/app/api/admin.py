"""
Admin endpoints for system management and emergency operations.

Provides administrative endpoints for connection pool management,
system diagnostics, and emergency recovery operations.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from ..database import get_db, get_connection_pool_status, engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/database/pool/reset")
async def reset_connection_pool():
    """
    Emergency endpoint to reset the database connection pool.
    
    This endpoint disposes the current connection pool and creates a new one.
    Use this as a last resort when the connection pool is exhausted and
    the system is unresponsive.
    
    ⚠️ WARNING: This will close all active database connections!
    
    Returns:
        dict: Reset operation status and new pool information
    """
    try:
        logger.warning("Emergency connection pool reset requested")
        
        # Get current pool status before reset
        old_pool_status = get_connection_pool_status()
        logger.info(f"Pool status before reset: {old_pool_status}")
        
        # Dispose the current connection pool
        engine.dispose()
        logger.info("Connection pool disposed")
        
        # Get new pool status after reset
        new_pool_status = get_connection_pool_status()
        logger.info(f"Pool status after reset: {new_pool_status}")
        
        return {
            "status": "success",
            "message": "Connection pool reset successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "old_pool_status": old_pool_status,
            "new_pool_status": new_pool_status
        }
        
    except Exception as e:
        logger.error(f"Failed to reset connection pool: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset connection pool: {str(e)}"
        )


@router.get("/database/pool/status")
async def get_pool_status():
    """
    Get detailed connection pool status for administrative monitoring.
    
    Returns:
        dict: Detailed connection pool statistics and health information
    """
    try:
        pool_status = get_connection_pool_status()
        
        # Calculate additional metrics
        checked_out = pool_status.get("checked_out_connections", 0)
        total_capacity = pool_status.get("total_connections", 1)
        utilization_percent = (checked_out / total_capacity) * 100 if total_capacity > 0 else 0
        
        # Determine health status
        if utilization_percent < 50:
            health_status = "excellent"
        elif utilization_percent < 70:
            health_status = "good"
        elif utilization_percent < 85:
            health_status = "warning"
        elif utilization_percent < 95:
            health_status = "critical"
        else:
            health_status = "emergency"
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health_status": health_status,
            "utilization_percent": round(utilization_percent, 2),
            "pool_stats": pool_status,
            "recommendations": _get_pool_recommendations(utilization_percent, pool_status)
        }
        
    except Exception as e:
        logger.error(f"Failed to get pool status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pool status: {str(e)}"
        )


@router.post("/database/pool/force-cleanup")
async def force_pool_cleanup():
    """
    Force cleanup of stale connections in the pool.
    
    This endpoint attempts to clean up potentially stale connections
    by invalidating them and forcing the pool to create fresh connections.
    
    Returns:
        dict: Cleanup operation status
    """
    try:
        logger.warning("Force pool cleanup requested")
        
        # Get status before cleanup
        old_status = get_connection_pool_status()
        
        # Force invalidate all connections in the pool
        # This will cause them to be recreated on next use
        pool = engine.pool
        pool.invalidate()
        logger.info("Connection pool invalidated - stale connections will be recreated")
        
        # Get status after cleanup
        new_status = get_connection_pool_status()
        
        return {
            "status": "success",
            "message": "Pool cleanup completed - stale connections invalidated",
            "timestamp": datetime.utcnow().isoformat(),
            "old_status": old_status,
            "new_status": new_status
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup pool: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cleanup pool: {str(e)}"
        )


def _get_pool_recommendations(utilization_percent: float, pool_stats: dict) -> list:
    """
    Generate recommendations based on pool utilization.
    
    Args:
        utilization_percent: Current pool utilization percentage
        pool_stats: Current pool statistics
        
    Returns:
        list: List of recommendation strings
    """
    recommendations = []
    
    if utilization_percent > 90:
        recommendations.append("URGENT: Pool utilization is critical. Consider increasing pool_size and max_overflow.")
        recommendations.append("Monitor for connection leaks or long-running transactions.")
    elif utilization_percent > 70:
        recommendations.append("WARNING: Pool utilization is high. Monitor closely and consider scaling.")
    elif utilization_percent < 20:
        recommendations.append("Pool utilization is low. Current settings appear adequate.")
    
    checked_out = pool_stats.get("checked_out_connections", 0)
    if checked_out > 20:
        recommendations.append(f"High number of checked out connections ({checked_out}). Investigate active queries.")
    
    return recommendations
