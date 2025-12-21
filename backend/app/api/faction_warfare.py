"""
Faction warfare API endpoints.

Provides endpoints for faction warfare statistics and warzone data.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..database import get_db
from ..models.faction_warfare import FactionWarfareSnapshot
from ..services.esi_client import esi_client
from ..logging_config import get_app_logger

router = APIRouter()
logger = get_app_logger(__name__)


@router.get("/overview")
async def get_faction_warfare_overview(db: Session = Depends(get_db)):
    """
    Get the latest faction warfare overview for the Minmatar/Amarr warzone.
    
    Returns:
        Latest warzone statistics including system control and kill data
    """
    logger.info("Fetching faction warfare overview")
    
    # Get the latest snapshot from database
    logger.debug("Querying database for latest faction warfare snapshot")
    latest_snapshot = db.query(FactionWarfareSnapshot).order_by(
        desc(FactionWarfareSnapshot.timestamp)
    ).first()
    
    if not latest_snapshot:
        # If no database data exists, fall back to live ESI data
        logger.warning("No faction warfare snapshot found in database, falling back to live ESI data")
        try:
            logger.debug("Connecting to ESI client for live data")
            async with esi_client as client:
                fw_systems = await client.get_faction_warfare_systems()
                logger.debug(f"Retrieved {len(fw_systems) if fw_systems else 0} faction warfare systems from ESI")
                
                if not fw_systems:
                    logger.error("No faction warfare data available from database or ESI")
                    raise HTTPException(status_code=503, detail="No faction warfare data available from database or ESI")
                
                # Filter for Minmatar/Amarr warzone systems
                minmatar_faction_id = 500002  # Minmatar Republic
                amarr_faction_id = 500003     # Amarr Empire
                
                warzone_systems = [
                    system for system in fw_systems
                    if system.get('occupier_faction_id') in [minmatar_faction_id, amarr_faction_id]
                    or system.get('owner_faction_id') in [minmatar_faction_id, amarr_faction_id]
                ]
                
                # Calculate basic statistics
                minmatar_controlled = len([
                    s for s in warzone_systems 
                    if s.get('occupier_faction_id') == minmatar_faction_id
                ])
                
                amarr_controlled = len([
                    s for s in warzone_systems 
                    if s.get('occupier_faction_id') == amarr_faction_id
                ])
                
                contested = len([
                    s for s in warzone_systems 
                    if s.get('contested', 0) == 1
                ])
                
                total_systems = len(warzone_systems)
                
                logger.info(f"Returning live ESI data: {total_systems} systems, {minmatar_controlled} Minmatar, {amarr_controlled} Amarr, {contested} contested")
                return {
                    "timestamp": datetime.utcnow(),
                    "source": "live_esi_fallback",
                    "minmatar": {
                        "systems_controlled": minmatar_controlled,
                        "systems_contested": len([s for s in warzone_systems if s.get('contested', 0) == 1 and s.get('occupier_faction_id') == minmatar_faction_id]),
                        "control_percentage": (minmatar_controlled / total_systems * 100) if total_systems > 0 else 0,
                        "total_capture_percent": 0.0,  # Not available from live data
                        "total_advantage_percent": 0.0,  # Not available from live data
                        "kills_24h": 0,  # Not available from live data
                        "losses_24h": 0,  # Not available from live data
                        "kills_value_24h": 0.0,  # Not available from live data
                        "losses_value_24h": 0.0,  # Not available from live data
                        "efficiency": 0.0  # Not available from live data
                    },
                    "amarr": {
                        "systems_controlled": amarr_controlled,
                        "systems_contested": len([s for s in warzone_systems if s.get('contested', 0) == 1 and s.get('occupier_faction_id') == amarr_faction_id]),
                        "control_percentage": (amarr_controlled / total_systems * 100) if total_systems > 0 else 0,
                        "total_capture_percent": 0.0,  # Not available from live data
                        "total_advantage_percent": 0.0,  # Not available from live data
                        "kills_24h": 0,  # Not available from live data
                        "losses_24h": 0,  # Not available from live data
                        "kills_value_24h": 0.0,  # Not available from live data
                        "losses_value_24h": 0.0,  # Not available from live data
                        "efficiency": 0.0  # Not available from live data
                    },
                    "warzone": {
                        "total_systems": total_systems,
                        "contested_systems": contested,
                        "contested_percentage": (contested / total_systems * 100) if total_systems > 0 else 0,
                        "total_kills_24h": 0,  # Not available from live data
                        "total_kill_value_24h": 0.0,  # Not available from live data
                        "activity_index": 0.0  # Not available from live data
                    }
                }
                
        except Exception as e:
            logger.error(f"Error fetching faction warfare data from ESI: {str(e)}", exc_info=True)
            raise HTTPException(status_code=503, detail=f"Error fetching faction warfare data: {str(e)}")
    
    # Get previous snapshot for trend calculation
    logger.debug("Querying for previous snapshot to calculate trends")
    previous_snapshot = db.query(FactionWarfareSnapshot).filter(
        FactionWarfareSnapshot.timestamp < latest_snapshot.timestamp
    ).order_by(desc(FactionWarfareSnapshot.timestamp)).first()
    
    # Calculate trends if previous data exists
    trends = {}
    if previous_snapshot:
        logger.debug("Calculating trends from previous snapshot")
        trends = {
            "minmatar_systems_change": latest_snapshot.minmatar_systems_controlled - previous_snapshot.minmatar_systems_controlled,
            "amarr_systems_change": latest_snapshot.amarr_systems_controlled - previous_snapshot.amarr_systems_controlled,
            "contested_systems_change": latest_snapshot.total_contested_systems - previous_snapshot.total_contested_systems,
            "time_period_hours": (latest_snapshot.timestamp - previous_snapshot.timestamp).total_seconds() / 3600
        }
    else:
        logger.debug("No previous snapshot found, trends will be empty")
    
    logger.info(f"Returning database snapshot from {latest_snapshot.timestamp}")
    return {
        "timestamp": latest_snapshot.timestamp,
        "source": "database",
        "trends": trends,
        "minmatar": {
            "systems_controlled": latest_snapshot.minmatar_systems_controlled,
            "systems_contested": latest_snapshot.minmatar_systems_contested,
            "control_percentage": latest_snapshot.minmatar_control_percentage,
            "total_capture_percent": latest_snapshot.minmatar_total_capture_percent,
            "total_advantage_percent": latest_snapshot.minmatar_total_advantage_percent,
            "kills_24h": latest_snapshot.minmatar_kills_last_24h,
            "losses_24h": latest_snapshot.minmatar_losses_last_24h,
            "kills_value_24h": latest_snapshot.minmatar_kills_value_last_24h,
            "losses_value_24h": latest_snapshot.minmatar_losses_value_last_24h,
            "efficiency": latest_snapshot.minmatar_efficiency
        },
        "amarr": {
            "systems_controlled": latest_snapshot.amarr_systems_controlled,
            "systems_contested": latest_snapshot.amarr_systems_contested,
            "control_percentage": latest_snapshot.amarr_control_percentage,
            "total_capture_percent": latest_snapshot.amarr_total_capture_percent,
            "total_advantage_percent": latest_snapshot.amarr_total_advantage_percent,
            "kills_24h": latest_snapshot.amarr_kills_last_24h,
            "losses_24h": latest_snapshot.amarr_losses_last_24h,
            "kills_value_24h": latest_snapshot.amarr_kills_value_last_24h,
            "losses_value_24h": latest_snapshot.amarr_losses_value_last_24h,
            "efficiency": latest_snapshot.amarr_efficiency
        },
        "warzone": {
            "total_systems": latest_snapshot.total_systems,
            "contested_systems": latest_snapshot.total_contested_systems,
            "contested_percentage": latest_snapshot.contested_percentage,
            "total_kills_24h": latest_snapshot.total_kills_last_24h,
            "total_kill_value_24h": latest_snapshot.total_kill_value_last_24h,
            "activity_index": latest_snapshot.activity_index
        }
    }


@router.get("/trends")
async def get_faction_warfare_trends(
    hours: int = Query(default=24, ge=1, le=168, description="Number of hours to look back"),
    db: Session = Depends(get_db)
):
    """
    Get faction warfare trends over time.
    
    Args:
        hours: Number of hours to look back (1-168, default 24)
        
    Returns:
        Time series data for faction warfare metrics
    """
    logger.info(f"Fetching faction warfare trends for last {hours} hours")
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    snapshots = db.query(FactionWarfareSnapshot).filter(
        FactionWarfareSnapshot.timestamp >= start_time
    ).order_by(FactionWarfareSnapshot.timestamp).all()
    
    logger.debug(f"Found {len(snapshots)} snapshots for trend analysis")
    
    if not snapshots:
        logger.warning(f"No trend data available for the last {hours} hours")
        raise HTTPException(status_code=404, detail="No trend data available for the specified period")
    
    return {
        "period": {
            "start": start_time,
            "end": datetime.utcnow(),
            "hours": hours
        },
        "data": [
            {
                "timestamp": snapshot.timestamp,
                "minmatar": {
                    "systems_controlled": snapshot.minmatar_systems_controlled,
                    "control_percentage": snapshot.minmatar_control_percentage,
                    "kills_24h": snapshot.minmatar_kills_last_24h,
                    "efficiency": snapshot.minmatar_efficiency
                },
                "amarr": {
                    "systems_controlled": snapshot.amarr_systems_controlled,
                    "control_percentage": snapshot.amarr_control_percentage,
                    "kills_24h": snapshot.amarr_kills_last_24h,
                    "efficiency": snapshot.amarr_efficiency
                },
                "warzone": {
                    "contested_systems": snapshot.total_contested_systems,
                    "activity_index": snapshot.activity_index
                }
            }
            for snapshot in snapshots
        ]
    }


@router.get("/live")
async def get_live_faction_warfare_data():
    """
    Get live faction warfare data directly from ESI API.
    
    Returns:
        Real-time faction warfare data from EVE Online
    """
    logger.info("Fetching live faction warfare data from ESI")
    try:
        logger.debug("Connecting to ESI client for live data")
        async with esi_client as client:
            # Fetch live data from ESI
            logger.debug("Fetching live faction warfare systems")
            fw_systems = await client.get_faction_warfare_systems()
            logger.debug("Fetching live faction warfare stats")
            fw_stats = await client.get_faction_warfare_stats()
            
            if not fw_systems:
                logger.error("Unable to fetch live faction warfare systems from ESI")
                raise HTTPException(status_code=503, detail="Unable to fetch live data from ESI")
            
            # Filter for Minmatar/Amarr warzone systems
            minmatar_faction_id = 500002  # Minmatar Republic
            amarr_faction_id = 500003     # Amarr Empire
            
            warzone_systems = [
                system for system in fw_systems
                if system.get('occupier_faction_id') in [minmatar_faction_id, amarr_faction_id]
                or system.get('owner_faction_id') in [minmatar_faction_id, amarr_faction_id]
            ]
            
            # Calculate basic statistics
            minmatar_controlled = len([
                s for s in warzone_systems 
                if s.get('occupier_faction_id') == minmatar_faction_id
            ])
            
            amarr_controlled = len([
                s for s in warzone_systems 
                if s.get('occupier_faction_id') == amarr_faction_id
            ])
            
            contested = len([
                s for s in warzone_systems 
                if s.get('contested', 0) == 1
            ])
            
            total_systems = len(warzone_systems)
            
            logger.info(f"Returning live ESI data: {total_systems} systems, {minmatar_controlled} Minmatar, {amarr_controlled} Amarr, {contested} contested")
            return {
                "timestamp": datetime.utcnow(),
                "source": "live_esi",
                "systems": warzone_systems,
                "summary": {
                    "total_systems": total_systems,
                    "minmatar_controlled": minmatar_controlled,
                    "amarr_controlled": amarr_controlled,
                    "contested": contested,
                    "minmatar_percentage": (minmatar_controlled / total_systems * 100) if total_systems > 0 else 0,
                    "amarr_percentage": (amarr_controlled / total_systems * 100) if total_systems > 0 else 0,
                    "contested_percentage": (contested / total_systems * 100) if total_systems > 0 else 0
                },
                "faction_stats": fw_stats
            }
            
    except Exception as e:
        logger.error(f"Error fetching live faction warfare data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Error fetching live data: {str(e)}")


@router.get("/leaderboards")
async def get_faction_warfare_leaderboards():
    """
    Get faction warfare leaderboards from ESI.
    
    Returns:
        Faction warfare leaderboard data
    """
    logger.info("Fetching faction warfare leaderboards")
    try:
        logger.debug("Connecting to ESI client for leaderboards")
        async with esi_client as client:
            leaderboards = await client.get_faction_warfare_leaderboards()
            
            if not leaderboards:
                logger.error("Unable to fetch leaderboard data from ESI")
                raise HTTPException(status_code=503, detail="Unable to fetch leaderboard data from ESI")
            
            logger.info("Successfully fetched faction warfare leaderboards")
            return {
                "timestamp": datetime.utcnow(),
                "leaderboards": leaderboards
            }
            
    except Exception as e:
        logger.error(f"Error fetching leaderboard data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=503, detail=f"Error fetching leaderboard data: {str(e)}")


@router.post("/collect-data")
async def trigger_data_collection():
    """
    Manually trigger faction warfare data collection.
    
    This endpoint allows manual triggering of the data collection task
    for testing and immediate data updates.
    
    Returns:
        Task result information
    """
    logger.info("Triggering faction warfare data collection task")
    try:
        from ..tasks.data_collection import collect_faction_warfare_data
        
        # Trigger the task
        result = collect_faction_warfare_data.delay()
        
        logger.info(f"Data collection task has been queued with ID: {result.id}")
        return {
            "status": "triggered",
            "task_id": result.id,
            "message": "Data collection task has been queued"
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger data collection task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger data collection: {str(e)}")


@router.post("/collect-data-now")
async def collect_data_immediately(db: Session = Depends(get_db)):
    """
    Immediately collect faction warfare data without using Celery.
    
    This endpoint directly processes ESI data and stores it in the database.
    Useful for initial setup or when Celery workers are not running.
    
    Returns:
        Collection result information
    """
    logger.info("Starting immediate faction warfare data collection")
    try:
        from ..services.data_processor import DataProcessor
        
        # Collect and process data
        logger.debug("Connecting to ESI client for data collection")
        async with esi_client as client:
            # Initialize data processor with ESI client
            logger.debug("Initializing data processor")
            data_processor = DataProcessor(db, client)
            
            # Ensure factions exist
            logger.debug("Ensuring factions exist in database")
            data_processor._ensure_factions_exist()
            
            # Get faction warfare systems from ESI
            logger.debug("Fetching faction warfare systems from ESI")
            fw_systems = await client.get_faction_warfare_systems()
            
            if not fw_systems:
                logger.error("Failed to fetch faction warfare systems from ESI")
                raise HTTPException(status_code=503, detail="Failed to fetch faction warfare systems from ESI")
            
            logger.debug(f"Retrieved {len(fw_systems)} faction warfare systems")
            
            # Get warzone data for advantage information
            logger.debug("Fetching warzone data for advantage information")
            warzone_data = await client.get_warzone_data()
            
            if not warzone_data:
                logger.warning("Failed to fetch warzone data - advantage percentages will be 0")
            
            # Get faction warfare stats
            logger.debug("Fetching faction warfare stats")
            fw_stats = await client.get_faction_warfare_stats()
            
            # Process all data together
            logger.debug("Processing faction warfare data")
            result = await data_processor.process_faction_warfare_data(
                fw_systems=fw_systems,
                fw_stats=fw_stats,
                warzone_data=warzone_data
            )
            
            # Commit changes
            logger.debug("Committing database changes")
            db.commit()
            
            logger.info(
                f"Data collection completed successfully: "
                f"{result.get('systems_processed', 0)} systems processed, "
                f"{result.get('snapshots_created', 0)} snapshots created"
            )
            
            return {
                "status": "completed",
                "message": "Data collection completed successfully",
                "systems_processed": result.get("systems_processed", 0),
                "snapshots_created": result.get("snapshots_created", 0),
                "systems_updated": result.get("systems_updated", 0),
                "warzone_snapshot_created": result.get("warzone_snapshot_created", False)
            }
            
    except Exception as e:
        logger.error(f"Failed to collect faction warfare data: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to collect data: {str(e)}")


@router.post("/collect-killmails-now")
async def collect_killmails_immediately(
    system_id: int = Query(..., description="System ID to collect killmails for"),
    db: Session = Depends(get_db)
):
    """
    Immediately collect killmail data for a specific system from Zkillboard API.
    
    This endpoint fetches killmail data for the specified system and processes it
    to track combat activity, player/corporation/alliance statistics.
    
    Args:
        system_id: EVE Online system ID to collect killmails for
        
    Returns:
        Collection result information including processing statistics
    """
    logger.info(f"Starting killmail collection for system {system_id}")
    try:
        from ..services.zkillboard_client import ZkillboardClient
        from ..services.killmail_processor import KillmailProcessor
        from ..models.system import System
        
        # Verify system exists and is a faction warfare system
        logger.debug(f"Verifying system {system_id} exists in database")
        system = db.query(System).filter(System.system_id == system_id).first()
        if not system:
            logger.error(f"System {system_id} not found in faction warfare systems")
            raise HTTPException(
                status_code=404, 
                detail=f"System {system_id} not found in faction warfare systems"
            )
        
        # Initialize clients
        logger.debug("Initializing Zkillboard client and killmail processor")
        zkillboard_client = ZkillboardClient()
        killmail_processor = KillmailProcessor()
        
        async with zkillboard_client:
            # Fetch killmails for the system (last 24 hours by default)
            logger.debug(f"Fetching killmails for system {system_id} ({system.name})")
            killmails = await zkillboard_client.get_system_all_activity(system_id)
            
            if not killmails:
                logger.info(f"No killmails found for system {system_id} ({system.name})")
                return {
                    "status": "completed",
                    "message": f"No killmails found for system {system_id} ({system.name})",
                    "system_id": system_id,
                    "system_name": system.name,
                    "killmails_processed": 0,
                    "killmails_stored": 0,
                    "killmails_skipped": 0
                }
            
            logger.debug(f"Retrieved {len(killmails)} killmails, processing...")
            
            # Process killmails
            result = await killmail_processor.process_system_killmails(
                system_id=system_id,
                killmails=killmails,
                db=db
            )
            
            # Commit changes
            logger.debug("Committing killmail data to database")
            db.commit()
            
            logger.info(
                f"Killmail collection completed for system {system_id} ({system.name}): "
                f"{len(killmails)} processed, {result.get('stored', 0)} stored, "
                f"{result.get('skipped', 0)} skipped, {result.get('errors', 0)} errors"
            )
            
            return {
                "status": "completed",
                "message": f"Killmail collection completed for system {system_id} ({system.name})",
                "system_id": system_id,
                "system_name": system.name,
                "killmails_processed": len(killmails),
                "killmails_stored": result.get("stored", 0),
                "killmails_skipped": result.get("skipped", 0),
                "errors": result.get("errors", 0)
            }
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Failed to collect killmails for system {system_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to collect killmails: {str(e)}")


@router.get("/leaderboard")
async def get_faction_warfare_leaderboard():
    """
    Get faction warfare leaderboard data from EVE Online API.
    
    This endpoint acts as a proxy to the EVE Online warzone leaderboard API
    to avoid CORS issues when calling from the frontend.
    
    Returns:
        Leaderboard data for all factions including kills and victory points rankings
    """
    import httpx
    
    logger.info("Fetching faction warfare leaderboard data")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.debug("Making request to EVE Online leaderboard API")
            response = await client.get("https://www.eveonline.com/api/warzone/leaderboard")
            
            if response.status_code != 200:
                logger.error(f"EVE Online API returned status {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=502, 
                    detail=f"Failed to fetch leaderboard data from EVE Online API (status: {response.status_code})"
                )
            
            leaderboard_data = response.json()
            logger.info("Successfully fetched leaderboard data from EVE Online API")
            
            return leaderboard_data
            
    except httpx.TimeoutException:
        logger.error("Timeout while fetching leaderboard data from EVE Online API")
        raise HTTPException(status_code=504, detail="Timeout while fetching leaderboard data")
    except httpx.RequestError as e:
        logger.error(f"Request error while fetching leaderboard data: {str(e)}")
        raise HTTPException(status_code=502, detail="Failed to connect to EVE Online API")
    except Exception as e:
        logger.error(f"Unexpected error while fetching leaderboard data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching leaderboard data")


@router.post("/trigger-killmail-automation")
async def trigger_killmail_automation():
    """
    Manually trigger the killmail collection automation.
    
    This endpoint allows manual triggering of the staggered killmail collection
    for all warzone systems. Useful for testing and immediate data collection.
    
    Returns:
        Task result information
    """
    logger.info("Manually triggering killmail collection automation")
    
    try:
        from ..tasks.data_collection import orchestrate_killmail_collection
        
        # Trigger the orchestration task
        result = orchestrate_killmail_collection.delay()
        
        logger.info(f"Killmail automation task has been queued with ID: {result.id}")
        
        return {
            "status": "queued",
            "task_id": result.id,
            "message": "Killmail collection automation has been queued"
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger killmail automation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger automation: {str(e)}")


@router.post("/trigger-general-data-automation")
async def trigger_general_data_automation():
    """
    Manually trigger the general warzone data collection automation.
    
    This endpoint allows manual triggering of the general warzone data collection.
    Useful for testing and immediate data collection.
    
    Returns:
        Task result information
    """
    logger.info("Manually triggering general warzone data collection automation")
    
    try:
        from ..tasks.data_collection import collect_general_warzone_data
        
        # Trigger the general data collection task
        result = collect_general_warzone_data.delay()
        
        logger.info(f"General data collection task has been queued with ID: {result.id}")
        
        return {
            "status": "queued",
            "task_id": result.id,
            "message": "General warzone data collection has been queued"
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger general data automation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to trigger automation: {str(e)}")


@router.get("/automation-status")
async def get_automation_status(db: Session = Depends(get_db)):
    """
    Get the status of the automation system.
    
    Returns information about the current state of automated data collection,
    including system counts and recent collection activity.
    
    Returns:
        Automation status information
    """
    logger.info("Fetching automation status")
    
    try:
        from ..models.system import System
        from ..models.killmail import Killmail
        from sqlalchemy import func
        
        # Get system count
        total_systems = db.query(System).count()
        
        # Get recent killmail activity (last 24 hours)
        recent_killmails = db.query(func.count(Killmail.killmail_id)).filter(
            Killmail.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).scalar()
        
        # Get systems with recent killmail data
        systems_with_recent_data = db.query(func.count(func.distinct(Killmail.system_id))).filter(
            Killmail.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).scalar()
        
        # Calculate estimated collection cycle time (5 minutes per system)
        estimated_cycle_time_minutes = total_systems * 5
        estimated_cycle_time_hours = estimated_cycle_time_minutes / 60
        
        logger.info(f"Automation status: {total_systems} systems, {recent_killmails} recent killmails")
        
        return {
            "status": "active",
            "timestamp": datetime.utcnow(),
            "warzone_systems": {
                "total_systems": total_systems,
                "systems_with_recent_killmails": systems_with_recent_data,
                "coverage_percentage": (systems_with_recent_data / total_systems * 100) if total_systems > 0 else 0
            },
            "collection_cycle": {
                "interval_minutes": 5,
                "estimated_cycle_time_minutes": estimated_cycle_time_minutes,
                "estimated_cycle_time_hours": round(estimated_cycle_time_hours, 2)
            },
            "recent_activity": {
                "killmails_last_24h": recent_killmails,
                "systems_active_last_24h": systems_with_recent_data
            },
            "automation_schedule": {
                "killmail_orchestration": "Every hour",
                "general_data_collection": "Every hour",
                "system_collection_interval": "5 minutes between systems"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get automation status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get automation status: {str(e)}")
