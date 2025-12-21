"""
Data collection tasks for faction warfare metrics.

This module contains Celery tasks that collect data from the ESI API
and store it in the database for historical analysis.
"""

import logging
import asyncio
import httpx
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


def get_warzone_system_ids(db: Session) -> List[int]:
    """
    Get all faction warfare system IDs from the database.
    
    Returns:
        List of system IDs for Minmatar/Amarr warzone systems
    """
    try:
        # Get all systems from the database (they should all be warzone systems)
        systems = db.query(System.system_id).all()
        system_ids = [system.system_id for system in systems]
        
        logger.info(f"Retrieved {len(system_ids)} warzone system IDs from database")
        return system_ids
        
    except Exception as e:
        logger.error(f"Failed to get warzone system IDs: {str(e)}", exc_info=True)
        return []


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_system_killmails(self, system_id: int):
    """
    Collect killmail data for a specific system.
    
    This task calls the existing killmail collection endpoint for a single system.
    
    Args:
        system_id: EVE system ID to collect killmails for
        
    Returns:
        dict: Collection results
    """
    logger.info(f"Starting killmail collection for system {system_id}")
    
    try:
        # Make HTTP request to the existing endpoint
        async def fetch_killmails():
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"http://backend:8000/api/v1/faction-warfare/collect-killmails-now",
                    params={"system_id": system_id}
                )
                
                if response.status_code != 200:
                    raise Exception(f"API returned status {response.status_code}: {response.text}")
                
                return response.json()
        
        # Run the async request
        result = asyncio.run(fetch_killmails())
        
        logger.info(f"Killmail collection completed for system {system_id}: {result.get('message', 'Success')}")
        
        return {
            "status": "success",
            "system_id": system_id,
            "timestamp": datetime.utcnow().isoformat(),
            "result": result
        }
        
    except Exception as exc:
        logger.error(f"Killmail collection failed for system {system_id}: {str(exc)}", exc_info=True)
        
        # Retry the task with exponential backoff
        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for killmail collection of system {system_id}")
            return {
                "status": "failed",
                "system_id": system_id,
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
                "retries": self.request.retries
            }


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def orchestrate_killmail_collection(self):
    """
    Orchestrate the staggered collection of killmails for all warzone systems.
    
    This task runs every hour and schedules individual system collections
    with 5-minute intervals between each system to avoid API rate limits.
    
    Returns:
        dict: Orchestration results
    """
    db = SessionLocal()
    
    try:
        logger.info("Starting killmail collection orchestration")
        
        # Get all warzone system IDs
        system_ids = get_warzone_system_ids(db)
        
        if not system_ids:
            logger.warning("No warzone systems found in database")
            return {
                "status": "warning",
                "message": "No warzone systems found in database",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        logger.info(f"Scheduling killmail collection for {len(system_ids)} systems")
        
        # Schedule individual system collections with 5-minute intervals
        scheduled_tasks = []
        base_time = datetime.utcnow()
        
        for i, system_id in enumerate(system_ids):
            # Calculate execution time: start immediately for first system, then 5-minute intervals
            execution_time = base_time + timedelta(minutes=i * 5)
            
            # Schedule the task
            task_result = collect_system_killmails.apply_async(
                args=[system_id],
                eta=execution_time
            )
            
            scheduled_tasks.append({
                "system_id": system_id,
                "task_id": task_result.id,
                "scheduled_time": execution_time.isoformat()
            })
            
            logger.debug(f"Scheduled system {system_id} for {execution_time}")
        
        total_duration_minutes = len(system_ids) * 5
        completion_time = base_time + timedelta(minutes=total_duration_minutes)
        
        logger.info(
            f"Killmail collection orchestration completed: "
            f"{len(scheduled_tasks)} tasks scheduled, "
            f"estimated completion at {completion_time}"
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "systems_scheduled": len(scheduled_tasks),
            "total_duration_minutes": total_duration_minutes,
            "estimated_completion": completion_time.isoformat(),
            "scheduled_tasks": scheduled_tasks[:5]  # Only return first 5 for brevity
        }
        
    except Exception as exc:
        logger.error(f"Killmail orchestration failed: {str(exc)}", exc_info=True)
        
        # Retry the task
        try:
            raise self.retry(exc=exc, countdown=300)  # Retry after 5 minutes
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for killmail orchestration")
            return {
                "status": "failed",
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
                "retries": self.request.retries
            }
    
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def collect_general_warzone_data(self):
    """
    Collect general warzone data using the existing endpoint.
    
    This task calls the collect-data-now endpoint to gather faction warfare
    statistics and system control data.
    
    Returns:
        dict: Collection results
    """
    logger.info("Starting general warzone data collection")
    
    try:
        # Make HTTP request to the existing endpoint
        async def fetch_warzone_data():
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    "http://backend:8000/api/v1/faction-warfare/collect-data-now"
                )
                
                if response.status_code != 200:
                    raise Exception(f"API returned status {response.status_code}: {response.text}")
                
                return response.json()
        
        # Run the async request
        result = asyncio.run(fetch_warzone_data())
        
        logger.info(f"General warzone data collection completed: {result.get('message', 'Success')}")
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "result": result
        }
        
    except Exception as exc:
        logger.error(f"General warzone data collection failed: {str(exc)}", exc_info=True)
        
        # Retry the task with exponential backoff
        try:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for general warzone data collection")
            return {
                "status": "failed",
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
                "retries": self.request.retries
            }


# Configure periodic tasks
celery_app.conf.beat_schedule = {
    'collect-faction-warfare-data': {
        'task': 'app.tasks.data_collection.collect_faction_warfare_data',
        'schedule': 3600.0,  # Every hour
    },
    'orchestrate-killmail-collection': {
        'task': 'app.tasks.data_collection.orchestrate_killmail_collection',
        'schedule': 3600.0,  # Every hour - starts the staggered collection
    },
    'collect-general-warzone-data': {
        'task': 'app.tasks.data_collection.collect_general_warzone_data',
        'schedule': 3600.0,  # Every hour - collects general warzone data
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
