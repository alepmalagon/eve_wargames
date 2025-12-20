"""
API endpoints for frontline classification and system adjacency data.
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.system import System
from ..services.esi_client import ESIClient
from ..utils.frontline_classifier import (
    get_frontline_classifier, 
    SystemClassification,
    get_system_adjacency
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/frontlines", tags=["frontlines"])


@router.get("/")
async def get_frontline_overview(
    db: Session = Depends(get_db)
):
    """
    Get frontline classification overview for all warzone systems.
    
    Returns:
        Dict with system classifications and statistics
    """
    try:
        # Get current system control data from database
        systems = db.query(System).all()
        
        if not systems:
            raise HTTPException(status_code=404, detail="No systems found in database")
        
        # Convert to format expected by classifier
        system_control_data = []
        for system in systems:
            system_control_data.append({
                "solar_system_id": system.system_id,
                "occupier_faction_id": system.controlling_faction_id
            })
        
        # Get classifier and classify systems
        classifier = get_frontline_classifier()
        classifications = classifier.classify_systems(system_control_data)
        
        # Get statistics
        stats = classifier.get_classification_stats(classifications)
        
        # Build response with system details
        systems_by_classification = {
            "frontline": [],
            "command_operations": [],
            "rearguard": []
        }
        
        for system in systems:
            classification = classifications.get(system.system_id)
            if classification:
                classification_key = classification.value
                system_info = {
                    "system_id": system.system_id,
                    "name": system.name,
                    "security_status": system.security_status,
                    "controlling_faction_id": system.controlling_faction_id,
                    "contested": system.contested,
                    "classification": classification_key,
                    "adjacent_systems": classifier.get_system_adjacency(system.system_id)
                }
                systems_by_classification[classification_key].append(system_info)
        
        return {
            "statistics": stats,
            "systems": systems_by_classification,
            "metadata": {
                "total_systems": len(systems),
                "classification_algorithm": "proximity-based",
                "description": "Frontline classification based on system adjacency and faction control"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting frontline overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get frontline overview: {str(e)}")


@router.get("/live")
async def get_live_frontline_data():
    """
    Get live frontline classification data using current ESI data.
    
    Returns:
        Dict with live system classifications
    """
    try:
        # Get live faction warfare data from ESI
        esi_client = ESIClient()
        fw_systems = await esi_client.get_faction_warfare_systems()
        
        if not fw_systems:
            raise HTTPException(status_code=503, detail="Failed to fetch live faction warfare data")
        
        # Filter to Minmatar/Amarr warzone
        minmatar_faction_id = 500002
        amarr_faction_id = 500003
        
        warzone_systems = []
        for system in fw_systems:
            occupier_faction_id = system.get('occupier_faction_id')
            owner_faction_id = system.get('owner_faction_id')
            
            if (occupier_faction_id in [minmatar_faction_id, amarr_faction_id] or 
                owner_faction_id in [minmatar_faction_id, amarr_faction_id]):
                warzone_systems.append(system)
        
        # Get classifier and classify systems
        classifier = get_frontline_classifier()
        classifications = classifier.classify_systems(warzone_systems)
        
        # Get statistics
        stats = classifier.get_classification_stats(classifications)
        
        # Build response with system details
        systems_by_classification = {
            "frontline": [],
            "command_operations": [],
            "rearguard": []
        }
        
        for system in warzone_systems:
            system_id = system['solar_system_id']
            classification = classifications.get(system_id)
            
            if classification:
                # Get system name from static data
                system_info_static = classifier.get_system_info(system_id)
                system_name = system_info_static.get('name', f'System_{system_id}') if system_info_static else f'System_{system_id}'
                
                classification_key = classification.value
                system_info = {
                    "system_id": system_id,
                    "name": system_name,
                    "occupier_faction_id": system.get('occupier_faction_id'),
                    "owner_faction_id": system.get('owner_faction_id'),
                    "contested": system.get('contested'),
                    "victory_points": system.get('victory_points', 0),
                    "victory_points_threshold": system.get('victory_points_threshold', 0),
                    "classification": classification_key,
                    "adjacent_systems": classifier.get_system_adjacency(system_id)
                }
                systems_by_classification[classification_key].append(system_info)
        
        return {
            "statistics": stats,
            "systems": systems_by_classification,
            "metadata": {
                "total_systems": len(warzone_systems),
                "data_source": "live_esi",
                "classification_algorithm": "proximity-based",
                "description": "Live frontline classification based on current ESI data"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting live frontline data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get live frontline data: {str(e)}")


@router.get("/system/{system_id}")
async def get_system_frontline_info(
    system_id: int,
    db: Session = Depends(get_db)
):
    """
    Get frontline classification and adjacency info for a specific system.
    
    Args:
        system_id: EVE system ID
        
    Returns:
        Dict with system classification and adjacent systems
    """
    try:
        # Get system from database
        system = db.query(System).filter(System.system_id == system_id).first()
        if not system:
            raise HTTPException(status_code=404, detail=f"System {system_id} not found")
        
        # Get all systems for classification context
        all_systems = db.query(System).all()
        system_control_data = []
        for sys in all_systems:
            system_control_data.append({
                "solar_system_id": sys.system_id,
                "occupier_faction_id": sys.controlling_faction_id
            })
        
        # Get classifier and classify
        classifier = get_frontline_classifier()
        classifications = classifier.classify_systems(system_control_data)
        
        classification = classifications.get(system_id)
        adjacent_systems = classifier.get_system_adjacency(system_id)
        
        # Get info about adjacent systems
        adjacent_system_info = []
        for adj_id in adjacent_systems:
            adj_system = db.query(System).filter(System.system_id == adj_id).first()
            if adj_system:
                adj_classification = classifications.get(adj_id)
                adjacent_system_info.append({
                    "system_id": adj_id,
                    "name": adj_system.name,
                    "controlling_faction_id": adj_system.controlling_faction_id,
                    "classification": adj_classification.value if adj_classification else "unknown"
                })
        
        return {
            "system_id": system.system_id,
            "name": system.name,
            "security_status": system.security_status,
            "controlling_faction_id": system.controlling_faction_id,
            "contested": system.contested,
            "classification": classification.value if classification else "unknown",
            "adjacent_systems": adjacent_system_info,
            "adjacency_count": len(adjacent_systems)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting system frontline info for {system_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get system frontline info: {str(e)}")


@router.get("/adjacency/{system_id}")
async def get_system_adjacency_info(system_id: int):
    """
    Get adjacency information for a specific system.
    
    Args:
        system_id: EVE system ID
        
    Returns:
        Dict with system adjacency data
    """
    try:
        classifier = get_frontline_classifier()
        adjacent_systems = classifier.get_system_adjacency(system_id)
        system_info = classifier.get_system_info(system_id)
        
        if system_info is None:
            raise HTTPException(status_code=404, detail=f"System {system_id} not found in warzone")
        
        # Get info about adjacent systems from static data
        adjacent_system_info = []
        for adj_id in adjacent_systems:
            adj_info = classifier.get_system_info(adj_id)
            if adj_info:
                adjacent_system_info.append({
                    "system_id": adj_id,
                    "name": adj_info.get('name', f'System_{adj_id}'),
                    "occupier_faction_id": adj_info.get('occupier_faction_id'),
                    "owner_faction_id": adj_info.get('owner_faction_id')
                })
        
        return {
            "system_id": system_id,
            "name": system_info.get('name', f'System_{system_id}'),
            "adjacent_systems": adjacent_system_info,
            "adjacency_count": len(adjacent_systems),
            "metadata": {
                "data_source": "static_adjacency_map",
                "description": "System adjacency based on stargate connections"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting adjacency info for {system_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get adjacency info: {str(e)}")


@router.get("/stats")
async def get_frontline_statistics(db: Session = Depends(get_db)):
    """
    Get frontline classification statistics.
    
    Returns:
        Dict with classification statistics
    """
    try:
        # Get current system control data from database
        systems = db.query(System).all()
        
        if not systems:
            raise HTTPException(status_code=404, detail="No systems found in database")
        
        # Convert to format expected by classifier
        system_control_data = []
        for system in systems:
            system_control_data.append({
                "solar_system_id": system.system_id,
                "occupier_faction_id": system.controlling_faction_id
            })
        
        # Get classifier and classify systems
        classifier = get_frontline_classifier()
        classifications = classifier.classify_systems(system_control_data)
        
        # Get statistics
        stats = classifier.get_classification_stats(classifications)
        
        # Add percentages
        total = stats['total']
        if total > 0:
            stats['frontline_percentage'] = round((stats['frontline'] / total) * 100, 1)
            stats['command_operations_percentage'] = round((stats['command_operations'] / total) * 100, 1)
            stats['rearguard_percentage'] = round((stats['rearguard'] / total) * 100, 1)
        
        return {
            "statistics": stats,
            "metadata": {
                "classification_algorithm": "proximity-based",
                "description": "Statistics for frontline classification of warzone systems"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting frontline statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get frontline statistics: {str(e)}")
