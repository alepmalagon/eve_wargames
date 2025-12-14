"""
Data collection tasks for faction warfare metrics.

This module contains Celery tasks that collect data from the ESI API
and store it in the database for historical analysis.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from celery import Celery
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..database import SessionLocal
from ..models.system import System, SystemSnapshot
from ..models.faction_warfare import FactionWarfareSnapshot
from ..services.esi_client import esi_client
from ..services.data_processor import DataProcessor
from ..config import settings

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    "eve_wargames",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def collect_faction_warfare_data(self):
    """
    Collect faction warfare data from ESI API and store in database.
    
    This task runs hourly to collect:
    - System control data (capture/advantage percentages)
    - Faction warfare statistics
    - Warzone-wide metrics
    
    Returns:
        dict: Collection results and statistics
    """
    db = SessionLocal()
    processor = DataProcessor(db)
    
    try:
        logger.info("Starting faction warfare data collection")
        
        # Check if we already have recent data (within last 50 minutes)
        # This prevents duplicate collection if task runs multiple times
        recent_snapshot = db.query(FactionWarfareSnapshot).filter(
            FactionWarfareSnapshot.timestamp >= datetime.utcnow() - timedelta(minutes=50)
        ).first()
        
        if recent_snapshot:
            logger.info(f"Recent data found from {recent_snapshot.timestamp}, skipping collection")
            return {
                "status": "skipped",
                "reason": "recent_data_exists",
                "last_collection": recent_snapshot.timestamp.isoformat()
            }
        
        # Fetch data from ESI API
        async def fetch_esi_data():
            async with esi_client as client:
                # Get faction warfare systems
                fw_systems = await client.get_faction_warfare_systems()
                if not fw_systems:
                    raise Exception("Failed to fetch faction warfare systems from ESI")
                
                # Get faction warfare statistics
                fw_stats = await client.get_faction_warfare_stats()
                
                return fw_systems, fw_stats
        
        # Run async data fetching
        import asyncio
        fw_systems, fw_stats = asyncio.run(fetch_esi_data())
        
        logger.info(f"Fetched {len(fw_systems)} systems from ESI")
        
        # Process and store the data
        results = processor.process_faction_warfare_data(fw_systems, fw_stats)
        
        logger.info(f"Data collection completed successfully: {results}")
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "systems_processed": results.get("systems_processed", 0),
            "snapshots_created": results.get("snapshots_created", 0),
            "warzone_snapshot_created": results.get("warzone_snapshot_created", False)
        }
        
    except Exception as exc:
        logger.error(f"Data collection failed: {str(exc)}", exc_info=True)
        
        # Retry the task with exponential backoff
        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for data collection task")
            return {
                "status": "failed",
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
                "retries": self.request.retries
            }
    
    finally:
        db.close()


@celery_app.task(bind=True)
def cleanup_old_data(self, days_to_keep: int = 90):
    """
    Clean up old data to prevent database bloat.
    
    Args:
        days_to_keep: Number of days of data to retain
        
    Returns:
        dict: Cleanup results
    """
    db = SessionLocal()
    
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Clean up old system snapshots
        deleted_snapshots = db.query(SystemSnapshot).filter(
            SystemSnapshot.timestamp < cutoff_date
        ).delete()
        
        # Clean up old faction warfare snapshots
        deleted_fw_snapshots = db.query(FactionWarfareSnapshot).filter(
            FactionWarfareSnapshot.timestamp < cutoff_date
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleaned up {deleted_snapshots} system snapshots and {deleted_fw_snapshots} FW snapshots")
        
        return {
            "status": "success",
            "deleted_system_snapshots": deleted_snapshots,
            "deleted_fw_snapshots": deleted_fw_snapshots,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Data cleanup failed: {str(exc)}", exc_info=True)
        db.rollback()
        return {
            "status": "failed",
            "error": str(exc)
        }
    
    finally:
        db.close()


@celery_app.task(bind=True)
def health_check_task(self):
    """
    Health check task to verify system components are working.
    
    Returns:
        dict: Health check results
    """
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "database": False,
        "esi_api": False,
        "recent_data": False
    }
    
    # Check database connectivity
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        results["database"] = True
        db.close()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    
    # Check ESI API connectivity
    try:
        import asyncio
        async def check_esi():
            async with esi_client as client:
                fw_systems = await client.get_faction_warfare_systems()
                return fw_systems is not None
        
        results["esi_api"] = asyncio.run(check_esi())
    except Exception as e:
        logger.error(f"ESI API health check failed: {e}")
    
    # Check for recent data
    try:
        db = SessionLocal()
        recent_snapshot = db.query(FactionWarfareSnapshot).filter(
            FactionWarfareSnapshot.timestamp >= datetime.utcnow() - timedelta(hours=2)
        ).first()
        results["recent_data"] = recent_snapshot is not None
        db.close()
    except Exception as e:
        logger.error(f"Recent data check failed: {e}")
    
    return results


# Configure periodic tasks
celery_app.conf.beat_schedule = {
    'collect-faction-warfare-data': {
        'task': 'app.tasks.data_collection.collect_faction_warfare_data',
        'schedule': 3600.0,  # Every hour
    },
    'cleanup-old-data': {
        'task': 'app.tasks.data_collection.cleanup_old_data',
        'schedule': 86400.0,  # Daily
        'kwargs': {'days_to_keep': 90}
    },
    'health-check': {
        'task': 'app.tasks.data_collection.health_check_task',
        'schedule': 300.0,  # Every 5 minutes
    },
}

celery_app.conf.timezone = 'UTC'
