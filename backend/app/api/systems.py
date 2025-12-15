"""
Systems API endpoints.

Provides endpoints for system-specific faction warfare data.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from ..database import get_db
from ..models.system import System, SystemSnapshot
from ..services.esi_client import esi_client
from ..services.killmail_processor import KillmailProcessor

router = APIRouter()


@router.get("/")
async def get_systems(
    faction_id: Optional[int] = Query(None, description="Filter by controlling faction ID"),
    contested_only: bool = Query(False, description="Show only contested systems"),
    db: Session = Depends(get_db)
):
    """
    Get all systems in the Minmatar/Amarr warzone.
    
    Args:
        faction_id: Filter by controlling faction (500002 for Minmatar, 500003 for Amarr)
        contested_only: Show only contested systems
        
    Returns:
        List of systems with current control status
    """
    query = db.query(System)
    
    if faction_id:
        query = query.filter(System.controlling_faction_id == faction_id)
    
    if contested_only:
        query = query.filter(System.contested == 1)
    
    systems = query.all()
    
    return [
        {
            "system_id": system.system_id,
            "name": system.name,
            "security_status": system.security_status,
            "controlling_faction_id": system.controlling_faction_id,
            "contested": bool(system.contested),
            "capture_percent": system.capture_percent,
            "advantage_percent": system.advantage_percent,
            "minmatar_advantage": system.minmatar_advantage,
            "amarr_advantage": system.amarr_advantage,
            "updated_at": system.updated_at
        }
        for system in systems
    ]


@router.get("/{system_id}")
async def get_system_details(
    system_id: int = Path(..., description="EVE system ID"),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific system.
    
    Args:
        system_id: EVE system ID
        
    Returns:
        Detailed system information including current status
    """
    system = db.query(System).filter(System.system_id == system_id).first()
    
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    
    # Get recent snapshots for trend data
    recent_snapshots = db.query(SystemSnapshot).filter(
        and_(
            SystemSnapshot.system_id == system_id,
            SystemSnapshot.timestamp >= datetime.utcnow() - timedelta(hours=24)
        )
    ).order_by(desc(SystemSnapshot.timestamp)).limit(24).all()
    
    return {
        "system_id": system.system_id,
        "name": system.name,
        "security_status": system.security_status,
        "controlling_faction_id": system.controlling_faction_id,
        "contested": bool(system.contested),
        "capture_percent": system.capture_percent,
        "advantage_percent": system.advantage_percent,
        "minmatar_advantage": system.minmatar_advantage,
        "amarr_advantage": system.amarr_advantage,
        "created_at": system.created_at,
        "updated_at": system.updated_at,
        "recent_snapshots": [
            {
                "timestamp": snapshot.timestamp,
                "controlling_faction_id": snapshot.controlling_faction_id,
                "contested": bool(snapshot.contested),
                "capture_percent": snapshot.capture_percent,
                "advantage_percent": snapshot.advantage_percent,
                "minmatar_advantage": snapshot.minmatar_advantage,
                "amarr_advantage": snapshot.amarr_advantage
            }
            for snapshot in recent_snapshots
        ]
    }


@router.get("/{system_id}/trends")
async def get_system_trends(
    system_id: int = Path(..., description="EVE system ID"),
    hours: int = Query(default=24, ge=1, le=168, description="Number of hours to look back"),
    db: Session = Depends(get_db)
):
    """
    Get historical trends for a specific system.
    
    Args:
        system_id: EVE system ID
        hours: Number of hours to look back (1-168, default 24)
        
    Returns:
        Time series data for system control metrics
    """
    system = db.query(System).filter(System.system_id == system_id).first()
    
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    snapshots = db.query(SystemSnapshot).filter(
        and_(
            SystemSnapshot.system_id == system_id,
            SystemSnapshot.timestamp >= start_time
        )
    ).order_by(SystemSnapshot.timestamp).all()
    
    if not snapshots:
        raise HTTPException(status_code=404, detail="No trend data available for the specified period")
    
    return {
        "system": {
            "system_id": system.system_id,
            "name": system.name
        },
        "period": {
            "start": start_time,
            "end": datetime.utcnow(),
            "hours": hours
        },
        "data": [
            {
                "timestamp": snapshot.timestamp,
                "controlling_faction_id": snapshot.controlling_faction_id,
                "contested": bool(snapshot.contested),
                "capture_percent": snapshot.capture_percent,
                "advantage_percent": snapshot.advantage_percent,
                "minmatar_advantage": snapshot.minmatar_advantage,
                "amarr_advantage": snapshot.amarr_advantage
            }
            for snapshot in snapshots
        ]
    }


@router.get("/{system_id}/live")
async def get_system_live_data(
    system_id: int = Path(..., description="EVE system ID")
):
    """
    Get live system data directly from ESI API.
    
    Args:
        system_id: EVE system ID
        
    Returns:
        Real-time system information from EVE Online
    """
    try:
        async with esi_client as client:
            # Get system info
            system_info = await client.get_system_info(system_id)
            
            if not system_info:
                raise HTTPException(status_code=404, detail="System not found in ESI")
            
            # Get faction warfare systems data
            fw_systems = await client.get_faction_warfare_systems()
            
            if fw_systems:
                # Find this system in the faction warfare data
                system_fw_data = next(
                    (s for s in fw_systems if s.get('solar_system_id') == system_id),
                    None
                )
            else:
                system_fw_data = None
            
            return {
                "timestamp": datetime.utcnow(),
                "source": "live_esi",
                "system_info": system_info,
                "faction_warfare_data": system_fw_data
            }
            
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error fetching live data: {str(e)}")


@router.get("/contested/")
async def get_contested_systems(db: Session = Depends(get_db)):
    """
    Get all currently contested systems.
    
    Returns:
        List of contested systems with control percentages
    """
    contested_systems = db.query(System).filter(System.contested == 1).all()
    
    return [
        {
            "system_id": system.system_id,
            "name": system.name,
            "security_status": system.security_status,
            "controlling_faction_id": system.controlling_faction_id,
            "capture_percent": system.capture_percent,
            "advantage_percent": system.advantage_percent,
            "updated_at": system.updated_at
        }
        for system in contested_systems
    ]


@router.get("/faction/{faction_id}")
async def get_systems_by_faction(
    faction_id: int = Path(..., description="Faction ID (500002 for Minmatar, 500003 for Amarr)"),
    db: Session = Depends(get_db)
):
    """
    Get all systems controlled by a specific faction.
    
    Args:
        faction_id: Faction ID (500002 for Minmatar, 500003 for Amarr)
        
    Returns:
        List of systems controlled by the faction
    """
    if faction_id not in [500002, 500003]:  # Minmatar and Amarr only
        raise HTTPException(status_code=400, detail="Invalid faction ID. Use 500002 for Minmatar or 500003 for Amarr")
    
    systems = db.query(System).filter(System.controlling_faction_id == faction_id).all()
    
    faction_name = "Minmatar Republic" if faction_id == 500002 else "Amarr Empire"
    
    return {
        "faction_id": faction_id,
        "faction_name": faction_name,
        "systems_controlled": len(systems),
        "systems": [
            {
                "system_id": system.system_id,
                "name": system.name,
                "security_status": system.security_status,
                "contested": bool(system.contested),
                "capture_percent": system.capture_percent,
                "advantage_percent": system.advantage_percent,
                "updated_at": system.updated_at
            }
            for system in systems
        ]
    }


@router.get("/{system_id}/killmail-stats")
async def get_system_killmail_stats(
    system_id: int = Path(..., description="EVE system ID"),
    time_window_hours: int = Query(default=24, ge=1, le=168, description="Time window in hours (1-168, default 24)"),
    db: Session = Depends(get_db)
):
    """
    Get killmail statistics for a specific system.
    
    Args:
        system_id: EVE system ID
        time_window_hours: Time window in hours to analyze (1-168, default 24)
        
    Returns:
        Killmail statistics including top players, corporations, and alliances
    """
    # Verify system exists
    system = db.query(System).filter(System.system_id == system_id).first()
    
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    
    # Initialize killmail processor
    processor = KillmailProcessor()
    
    try:
        # Get top performers
        top_players = processor.get_top_players(system_id, db, limit=5, time_window_hours=time_window_hours)
        top_corporations = processor.get_top_corporations(system_id, db, limit=5, time_window_hours=time_window_hours)
        top_alliances = processor.get_top_alliances(system_id, db, limit=5, time_window_hours=time_window_hours)
        
        # Get the most active ones (first in each list)
        most_active_player = top_players[0] if top_players else None
        most_active_corporation = top_corporations[0] if top_corporations else None
        most_active_alliance = top_alliances[0] if top_alliances else None
        
        return {
            "system": {
                "system_id": system.system_id,
                "name": system.name
            },
            "time_window_hours": time_window_hours,
            "most_active": {
                "player": most_active_player,
                "corporation": most_active_corporation,
                "alliance": most_active_alliance
            },
            "top_performers": {
                "players": top_players,
                "corporations": top_corporations,
                "alliances": top_alliances
            },
            "generated_at": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching killmail statistics: {str(e)}")
