"""
Kills API endpoints.

Provides endpoints for kill statistics and killmail data.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func

from ..database import get_db
from ..models.kills import Kill, KillStatistic

router = APIRouter()


@router.get("/statistics")
async def get_kill_statistics(
    system_id: Optional[int] = Query(None, description="Filter by system ID"),
    faction_id: Optional[int] = Query(None, description="Filter by faction ID"),
    corporation_id: Optional[int] = Query(None, description="Filter by corporation ID"),
    alliance_id: Optional[int] = Query(None, description="Filter by alliance ID"),
    period_type: str = Query(default="day", description="Period type: hour, day, week, month"),
    hours: int = Query(default=24, ge=1, le=168, description="Number of hours to look back"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated kill statistics.
    
    Args:
        system_id: Filter by system ID
        faction_id: Filter by faction ID (500002 for Minmatar, 500003 for Amarr)
        corporation_id: Filter by corporation ID
        alliance_id: Filter by alliance ID
        period_type: Aggregation period (hour, day, week, month)
        hours: Number of hours to look back
        
    Returns:
        Aggregated kill statistics for the specified filters and period
    """
    if period_type not in ["hour", "day", "week", "month"]:
        raise HTTPException(status_code=400, detail="Invalid period_type. Use: hour, day, week, month")
    
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(KillStatistic).filter(
        and_(
            KillStatistic.period_type == period_type,
            KillStatistic.period_start >= start_time
        )
    )
    
    if system_id:
        query = query.filter(KillStatistic.system_id == system_id)
    
    if faction_id:
        query = query.filter(KillStatistic.faction_id == faction_id)
    
    if corporation_id:
        query = query.filter(KillStatistic.corporation_id == corporation_id)
    
    if alliance_id:
        query = query.filter(KillStatistic.alliance_id == alliance_id)
    
    statistics = query.order_by(desc(KillStatistic.period_start)).all()
    
    return {
        "period": {
            "start": start_time,
            "end": datetime.utcnow(),
            "hours": hours,
            "type": period_type
        },
        "filters": {
            "system_id": system_id,
            "faction_id": faction_id,
            "corporation_id": corporation_id,
            "alliance_id": alliance_id
        },
        "statistics": [
            {
                "period_start": stat.period_start,
                "period_end": stat.period_end,
                "kills_count": stat.kills_count,
                "losses_count": stat.losses_count,
                "kills_value": stat.kills_value,
                "losses_value": stat.losses_value,
                "efficiency": stat.efficiency,
                "system_id": stat.system_id,
                "faction_id": stat.faction_id,
                "corporation_id": stat.corporation_id,
                "alliance_id": stat.alliance_id
            }
            for stat in statistics
        ]
    }


@router.get("/recent")
async def get_recent_kills(
    system_id: Optional[int] = Query(None, description="Filter by system ID"),
    faction_id: Optional[int] = Query(None, description="Filter by victim or attacker faction ID"),
    hours: int = Query(default=24, ge=1, le=168, description="Number of hours to look back"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of kills to return"),
    db: Session = Depends(get_db)
):
    """
    Get recent killmails.
    
    Args:
        system_id: Filter by system ID
        faction_id: Filter by victim or attacker faction ID
        hours: Number of hours to look back
        limit: Maximum number of kills to return
        
    Returns:
        List of recent killmails
    """
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(Kill).filter(Kill.kill_time >= start_time)
    
    if system_id:
        query = query.filter(Kill.system_id == system_id)
    
    if faction_id:
        query = query.filter(
            (Kill.victim_faction_id == faction_id) |
            (Kill.final_blow_faction_id == faction_id)
        )
    
    kills = query.order_by(desc(Kill.kill_time)).limit(limit).all()
    
    return {
        "period": {
            "start": start_time,
            "end": datetime.utcnow(),
            "hours": hours
        },
        "filters": {
            "system_id": system_id,
            "faction_id": faction_id
        },
        "total_kills": len(kills),
        "kills": [
            {
                "killmail_id": kill.killmail_id,
                "system_id": kill.system_id,
                "kill_time": kill.kill_time,
                "total_value": kill.total_value,
                "attacker_count": kill.attacker_count,
                "victim": {
                    "character_id": kill.victim_character_id,
                    "corporation_id": kill.victim_corporation_id,
                    "alliance_id": kill.victim_alliance_id,
                    "faction_id": kill.victim_faction_id,
                    "ship_type_id": kill.victim_ship_type_id
                },
                "final_blow": {
                    "character_id": kill.final_blow_character_id,
                    "corporation_id": kill.final_blow_corporation_id,
                    "alliance_id": kill.final_blow_alliance_id,
                    "faction_id": kill.final_blow_faction_id,
                    "ship_type_id": kill.final_blow_ship_type_id
                }
            }
            for kill in kills
        ]
    }


@router.get("/system/{system_id}")
async def get_system_kill_statistics(
    system_id: int = Path(..., description="EVE system ID"),
    hours: int = Query(default=24, ge=1, le=168, description="Number of hours to look back"),
    db: Session = Depends(get_db)
):
    """
    Get kill statistics for a specific system.
    
    Args:
        system_id: EVE system ID
        hours: Number of hours to look back
        
    Returns:
        Kill statistics for the system
    """
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    # Get raw kill counts
    total_kills = db.query(func.count(Kill.killmail_id)).filter(
        and_(
            Kill.system_id == system_id,
            Kill.kill_time >= start_time
        )
    ).scalar()
    
    # Get faction-specific statistics
    minmatar_kills = db.query(func.count(Kill.killmail_id)).filter(
        and_(
            Kill.system_id == system_id,
            Kill.kill_time >= start_time,
            Kill.final_blow_faction_id == 500002  # Minmatar
        )
    ).scalar()
    
    amarr_kills = db.query(func.count(Kill.killmail_id)).filter(
        and_(
            Kill.system_id == system_id,
            Kill.kill_time >= start_time,
            Kill.final_blow_faction_id == 500003  # Amarr
        )
    ).scalar()
    
    minmatar_losses = db.query(func.count(Kill.killmail_id)).filter(
        and_(
            Kill.system_id == system_id,
            Kill.kill_time >= start_time,
            Kill.victim_faction_id == 500002  # Minmatar
        )
    ).scalar()
    
    amarr_losses = db.query(func.count(Kill.killmail_id)).filter(
        and_(
            Kill.system_id == system_id,
            Kill.kill_time >= start_time,
            Kill.victim_faction_id == 500003  # Amarr
        )
    ).scalar()
    
    # Get value statistics
    total_value = db.query(func.sum(Kill.total_value)).filter(
        and_(
            Kill.system_id == system_id,
            Kill.kill_time >= start_time
        )
    ).scalar() or 0.0
    
    return {
        "system_id": system_id,
        "period": {
            "start": start_time,
            "end": datetime.utcnow(),
            "hours": hours
        },
        "total_kills": total_kills or 0,
        "total_value": total_value,
        "factions": {
            "minmatar": {
                "kills": minmatar_kills or 0,
                "losses": minmatar_losses or 0,
                "efficiency": (minmatar_kills / (minmatar_kills + minmatar_losses)) if (minmatar_kills + minmatar_losses) > 0 else 0.0
            },
            "amarr": {
                "kills": amarr_kills or 0,
                "losses": amarr_losses or 0,
                "efficiency": (amarr_kills / (amarr_kills + amarr_losses)) if (amarr_kills + amarr_losses) > 0 else 0.0
            }
        }
    }


@router.get("/faction/{faction_id}")
async def get_faction_kill_statistics(
    faction_id: int = Path(..., description="Faction ID (500002 for Minmatar, 500003 for Amarr)"),
    hours: int = Query(default=24, ge=1, le=168, description="Number of hours to look back"),
    db: Session = Depends(get_db)
):
    """
    Get kill statistics for a specific faction.
    
    Args:
        faction_id: Faction ID (500002 for Minmatar, 500003 for Amarr)
        hours: Number of hours to look back
        
    Returns:
        Kill statistics for the faction
    """
    if faction_id not in [500002, 500003]:
        raise HTTPException(status_code=400, detail="Invalid faction ID. Use 500002 for Minmatar or 500003 for Amarr")
    
    start_time = datetime.utcnow() - timedelta(hours=hours)
    faction_name = "Minmatar Republic" if faction_id == 500002 else "Amarr Empire"
    
    # Get kills by this faction
    kills_count = db.query(func.count(Kill.killmail_id)).filter(
        and_(
            Kill.final_blow_faction_id == faction_id,
            Kill.kill_time >= start_time
        )
    ).scalar() or 0
    
    # Get losses by this faction
    losses_count = db.query(func.count(Kill.killmail_id)).filter(
        and_(
            Kill.victim_faction_id == faction_id,
            Kill.kill_time >= start_time
        )
    ).scalar() or 0
    
    # Get kill values
    kills_value = db.query(func.sum(Kill.total_value)).filter(
        and_(
            Kill.final_blow_faction_id == faction_id,
            Kill.kill_time >= start_time
        )
    ).scalar() or 0.0
    
    losses_value = db.query(func.sum(Kill.total_value)).filter(
        and_(
            Kill.victim_faction_id == faction_id,
            Kill.kill_time >= start_time
        )
    ).scalar() or 0.0
    
    # Calculate efficiency
    total_value = kills_value + losses_value
    efficiency = (kills_value / total_value) if total_value > 0 else 0.0
    
    # Get system breakdown
    system_stats = db.query(
        Kill.system_id,
        func.count(Kill.killmail_id).label('kill_count')
    ).filter(
        and_(
            (Kill.final_blow_faction_id == faction_id) | (Kill.victim_faction_id == faction_id),
            Kill.kill_time >= start_time
        )
    ).group_by(Kill.system_id).all()
    
    return {
        "faction_id": faction_id,
        "faction_name": faction_name,
        "period": {
            "start": start_time,
            "end": datetime.utcnow(),
            "hours": hours
        },
        "kills": kills_count,
        "losses": losses_count,
        "kills_value": kills_value,
        "losses_value": losses_value,
        "efficiency": efficiency,
        "system_breakdown": [
            {
                "system_id": stat.system_id,
                "kill_count": stat.kill_count
            }
            for stat in system_stats
        ]
    }


@router.get("/trends")
async def get_kill_trends(
    faction_id: Optional[int] = Query(None, description="Filter by faction ID"),
    system_id: Optional[int] = Query(None, description="Filter by system ID"),
    hours: int = Query(default=24, ge=1, le=168, description="Number of hours to look back"),
    db: Session = Depends(get_db)
):
    """
    Get kill trends over time.
    
    Args:
        faction_id: Filter by faction ID
        system_id: Filter by system ID
        hours: Number of hours to look back
        
    Returns:
        Time series data for kill statistics
    """
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(KillStatistic).filter(
        and_(
            KillStatistic.period_type == "hour",
            KillStatistic.period_start >= start_time
        )
    )
    
    if faction_id:
        query = query.filter(KillStatistic.faction_id == faction_id)
    
    if system_id:
        query = query.filter(KillStatistic.system_id == system_id)
    
    statistics = query.order_by(KillStatistic.period_start).all()
    
    return {
        "period": {
            "start": start_time,
            "end": datetime.utcnow(),
            "hours": hours
        },
        "filters": {
            "faction_id": faction_id,
            "system_id": system_id
        },
        "data": [
            {
                "timestamp": stat.period_start,
                "kills_count": stat.kills_count,
                "losses_count": stat.losses_count,
                "kills_value": stat.kills_value,
                "losses_value": stat.losses_value,
                "efficiency": stat.efficiency
            }
            for stat in statistics
        ]
    }
