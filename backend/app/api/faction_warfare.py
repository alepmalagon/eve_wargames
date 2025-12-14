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

router = APIRouter()


@router.get("/overview")
async def get_faction_warfare_overview(db: Session = Depends(get_db)):
    """
    Get the latest faction warfare overview for the Minmatar/Amarr warzone.
    
    Returns:
        Latest warzone statistics including system control and kill data
    """
    # Get the latest snapshot from database
    latest_snapshot = db.query(FactionWarfareSnapshot).order_by(
        desc(FactionWarfareSnapshot.timestamp)
    ).first()
    
    if not latest_snapshot:
        # If no database data exists, fall back to live ESI data
        try:
            async with esi_client as client:
                fw_systems = await client.get_faction_warfare_systems()
                
                if not fw_systems:
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
            raise HTTPException(status_code=503, detail=f"Error fetching faction warfare data: {str(e)}")
    
    # Get previous snapshot for trend calculation
    previous_snapshot = db.query(FactionWarfareSnapshot).filter(
        FactionWarfareSnapshot.timestamp < latest_snapshot.timestamp
    ).order_by(desc(FactionWarfareSnapshot.timestamp)).first()
    
    # Calculate trends if previous data exists
    trends = {}
    if previous_snapshot:
        trends = {
            "minmatar_systems_change": latest_snapshot.minmatar_systems_controlled - previous_snapshot.minmatar_systems_controlled,
            "amarr_systems_change": latest_snapshot.amarr_systems_controlled - previous_snapshot.amarr_systems_controlled,
            "contested_systems_change": latest_snapshot.total_contested_systems - previous_snapshot.total_contested_systems,
            "time_period_hours": (latest_snapshot.timestamp - previous_snapshot.timestamp).total_seconds() / 3600
        }
    
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
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    snapshots = db.query(FactionWarfareSnapshot).filter(
        FactionWarfareSnapshot.timestamp >= start_time
    ).order_by(FactionWarfareSnapshot.timestamp).all()
    
    if not snapshots:
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
    try:
        async with esi_client as client:
            # Fetch live data from ESI
            fw_systems = await client.get_faction_warfare_systems()
            fw_stats = await client.get_faction_warfare_stats()
            
            if not fw_systems:
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
        raise HTTPException(status_code=503, detail=f"Error fetching live data: {str(e)}")


@router.get("/leaderboards")
async def get_faction_warfare_leaderboards():
    """
    Get faction warfare leaderboards from ESI.
    
    Returns:
        Faction warfare leaderboard data
    """
    try:
        async with esi_client as client:
            leaderboards = await client.get_faction_warfare_leaderboards()
            
            if not leaderboards:
                raise HTTPException(status_code=503, detail="Unable to fetch leaderboard data from ESI")
            
            return {
                "timestamp": datetime.utcnow(),
                "leaderboards": leaderboards
            }
            
    except Exception as e:
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
    try:
        from ..tasks.data_collection import collect_faction_warfare_data
        
        # Trigger the task
        result = collect_faction_warfare_data.delay()
        
        return {
            "status": "triggered",
            "task_id": result.id,
            "message": "Data collection task has been queued"
        }
        
    except Exception as e:
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
    try:
        from ..services.data_processor import DataProcessor
        
        # Collect and process data
        async with esi_client as client:
            # Initialize data processor with ESI client
            data_processor = DataProcessor(db, client)
            
            # Ensure factions exist
            data_processor._ensure_factions_exist()
            
            # Get faction warfare systems
            fw_systems = await client.get_faction_warfare_systems()
            
            if not fw_systems:
                raise HTTPException(status_code=503, detail="Failed to fetch faction warfare systems from ESI")
            
            # Filter for Minmatar/Amarr warzone
            warzone_systems = data_processor._filter_warzone_systems(fw_systems)
            
            if not warzone_systems:
                return {
                    "status": "completed",
                    "message": "No warzone systems found (this might be normal)",
                    "systems_processed": 0,
                    "snapshots_created": 0
                }
            
            # Process systems
            result = await data_processor._process_systems(warzone_systems)
            
            # Create warzone snapshot
            fw_stats = await client.get_faction_warfare_stats()
            warzone_result = data_processor._create_warzone_snapshot(warzone_systems, fw_stats)
            
            # Commit changes
            db.commit()
            
            return {
                "status": "completed",
                "message": "Data collection completed successfully",
                "systems_processed": len(warzone_systems),
                "snapshots_created": result.get("snapshots_created", 0),
                "systems_updated": result.get("systems_updated", 0),
                "warzone_snapshot_created": bool(warzone_result)
            }
            
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to collect data: {str(e)}")
