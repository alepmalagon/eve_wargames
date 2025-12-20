"""
Frontline classification utilities for EVE Online faction warfare systems.

This module provides functionality to classify systems as frontline, command operations,
or rearguard based on system adjacency and current faction control.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)

# Path to the static adjacency data file
ADJACENCY_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "system_adjacency.json"

# Militia faction IDs
MINMATAR_FACTION_ID = 500002  # Tribal Liberation Force
AMARR_FACTION_ID = 500003     # 24th Imperial Crusade


class SystemClassification(Enum):
    """System classification types."""
    FRONTLINE = "frontline"
    COMMAND_OPERATIONS = "command_operations"
    REARGUARD = "rearguard"


class FrontlineClassifier:
    """
    Classifier for determining system frontline status based on adjacency and control.
    """
    
    def __init__(self):
        self.adjacency_map: Dict[int, List[int]] = {}
        self.system_info: Dict[int, Dict] = {}
        self._load_adjacency_data()
    
    def _load_adjacency_data(self):
        """Load the static adjacency data from JSON file."""
        try:
            if not ADJACENCY_DATA_PATH.exists():
                logger.error(f"Adjacency data file not found: {ADJACENCY_DATA_PATH}")
                return
            
            with open(ADJACENCY_DATA_PATH, 'r') as f:
                data = json.load(f)
            
            # Convert string keys to integers for adjacency map
            self.adjacency_map = {
                int(system_id): adjacent_systems 
                for system_id, adjacent_systems in data.get('adjacency_map', {}).items()
            }
            
            # Convert string keys to integers for system info
            self.system_info = {
                int(system_id): info 
                for system_id, info in data.get('system_info', {}).items()
            }
            
            logger.info(f"Loaded adjacency data for {len(self.adjacency_map)} systems")
            
        except Exception as e:
            logger.error(f"Failed to load adjacency data: {e}")
            self.adjacency_map = {}
            self.system_info = {}
    
    def get_system_adjacency(self, system_id: int) -> List[int]:
        """
        Get the list of adjacent systems for a given system.
        
        Args:
            system_id: The system ID to get adjacency for
            
        Returns:
            List of adjacent system IDs
        """
        return self.adjacency_map.get(system_id, [])
    
    def get_system_info(self, system_id: int) -> Optional[Dict]:
        """
        Get system information from the static data.
        
        Args:
            system_id: The system ID to get info for
            
        Returns:
            System information dict or None if not found
        """
        return self.system_info.get(system_id)
    
    def classify_systems(self, system_control_data: List[Dict]) -> Dict[int, SystemClassification]:
        """
        Classify all systems based on current control data.
        
        Args:
            system_control_data: List of system control data from ESI/database
                Each dict should have: solar_system_id, occupier_faction_id
                
        Returns:
            Dict mapping system_id to SystemClassification
        """
        # Create ownership map from current data
        ownership_map = {}
        for system in system_control_data:
            system_id = system.get('solar_system_id') or system.get('system_id')
            occupier_faction_id = system.get('occupier_faction_id')
            ownership_map[system_id] = occupier_faction_id
        
        classifications = {}
        
        # First pass: Identify frontline systems
        frontline_systems = set()
        for system_id in self.adjacency_map.keys():
            if self._is_frontline_system(system_id, ownership_map):
                classifications[system_id] = SystemClassification.FRONTLINE
                frontline_systems.add(system_id)
        
        # Second pass: Identify command operations (adjacent to frontline)
        command_ops_systems = set()
        for system_id in self.adjacency_map.keys():
            if system_id in frontline_systems:
                continue  # Already classified as frontline
                
            if self._is_command_operations_system(system_id, frontline_systems):
                classifications[system_id] = SystemClassification.COMMAND_OPERATIONS
                command_ops_systems.add(system_id)
        
        # Third pass: Everything else is rearguard
        for system_id in self.adjacency_map.keys():
            if system_id not in classifications:
                classifications[system_id] = SystemClassification.REARGUARD
        
        logger.info(f"Classified {len(frontline_systems)} frontline, "
                   f"{len(command_ops_systems)} command ops, "
                   f"{len(classifications) - len(frontline_systems) - len(command_ops_systems)} rearguard systems")
        
        return classifications
    
    def _is_frontline_system(self, system_id: int, ownership_map: Dict[int, int]) -> bool:
        """
        Check if a system is frontline (adjacent to enemy-controlled system).
        
        Args:
            system_id: System to check
            ownership_map: Map of system_id -> occupier_faction_id
            
        Returns:
            True if system is frontline
        """
        system_faction = ownership_map.get(system_id)
        if not system_faction:
            return False
        
        adjacent_systems = self.adjacency_map.get(system_id, [])
        
        for adjacent_id in adjacent_systems:
            adjacent_faction = ownership_map.get(adjacent_id)
            
            # If adjacent system is controlled by enemy faction, this is frontline
            if self._are_enemy_factions(system_faction, adjacent_faction):
                return True
        
        return False
    
    def _is_command_operations_system(self, system_id: int, frontline_systems: Set[int]) -> bool:
        """
        Check if a system is command operations (adjacent to frontline system).
        
        Args:
            system_id: System to check
            frontline_systems: Set of frontline system IDs
            
        Returns:
            True if system is command operations
        """
        adjacent_systems = self.adjacency_map.get(system_id, [])
        
        for adjacent_id in adjacent_systems:
            if adjacent_id in frontline_systems:
                return True
        
        return False
    
    def _are_enemy_factions(self, faction1: int, faction2: int) -> bool:
        """
        Check if two factions are enemies in the Minmatar/Amarr warzone.
        
        Args:
            faction1: First faction ID
            faction2: Second faction ID
            
        Returns:
            True if factions are enemies
        """
        if not faction1 or not faction2:
            return False
        
        return ((faction1 == MINMATAR_FACTION_ID and faction2 == AMARR_FACTION_ID) or
                (faction1 == AMARR_FACTION_ID and faction2 == MINMATAR_FACTION_ID))
    
    def get_classification_stats(self, classifications: Dict[int, SystemClassification]) -> Dict[str, int]:
        """
        Get statistics about system classifications.
        
        Args:
            classifications: Dict mapping system_id to SystemClassification
            
        Returns:
            Dict with counts for each classification type
        """
        stats = {
            "frontline": 0,
            "command_operations": 0,
            "rearguard": 0,
            "total": len(classifications)
        }
        
        for classification in classifications.values():
            if classification == SystemClassification.FRONTLINE:
                stats["frontline"] += 1
            elif classification == SystemClassification.COMMAND_OPERATIONS:
                stats["command_operations"] += 1
            elif classification == SystemClassification.REARGUARD:
                stats["rearguard"] += 1
        
        return stats


# Global classifier instance
_classifier_instance: Optional[FrontlineClassifier] = None


def get_frontline_classifier() -> FrontlineClassifier:
    """
    Get the global frontline classifier instance.
    
    Returns:
        FrontlineClassifier instance
    """
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = FrontlineClassifier()
    return _classifier_instance


def classify_system(system_id: int, system_control_data: List[Dict]) -> Optional[SystemClassification]:
    """
    Classify a single system based on current control data.
    
    Args:
        system_id: System ID to classify
        system_control_data: List of all system control data
        
    Returns:
        SystemClassification or None if system not found
    """
    classifier = get_frontline_classifier()
    classifications = classifier.classify_systems(system_control_data)
    return classifications.get(system_id)


def get_system_adjacency(system_id: int) -> List[int]:
    """
    Get adjacent systems for a given system.
    
    Args:
        system_id: System ID to get adjacency for
        
    Returns:
        List of adjacent system IDs
    """
    classifier = get_frontline_classifier()
    return classifier.get_system_adjacency(system_id)
