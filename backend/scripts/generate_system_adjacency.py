#!/usr/bin/env python3
"""
Generate system adjacency data for the Minmatar/Amarr warzone.

This script fetches all warzone systems and builds an adjacency map by querying
the ESI API for stargate connections. The result is saved as a static JSON file
that can be used for frontline classification.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional
import aiohttp
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ESI API base URL
ESI_BASE_URL = "https://esi.evetech.net/latest"

# Militia faction IDs for Minmatar/Amarr warzone
MINMATAR_FACTION_ID = 500002  # Tribal Liberation Force
AMARR_FACTION_ID = 500003     # 24th Imperial Crusade


class ESIClient:
    """Simple ESI client for fetching system and stargate data."""
    
    def __init__(self):
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_faction_warfare_systems(self) -> Optional[List[Dict]]:
        """Get all faction warfare systems from ESI."""
        url = f"{ESI_BASE_URL}/fw/systems/"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Fetched {len(data)} faction warfare systems")
                    return data
                else:
                    logger.error(f"Failed to fetch FW systems: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching FW systems: {e}")
            return None
    
    async def get_system_info(self, system_id: int) -> Optional[Dict]:
        """Get system information including stargates."""
        url = f"{ESI_BASE_URL}/universe/systems/{system_id}/"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.warning(f"Failed to fetch system {system_id}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching system {system_id}: {e}")
            return None
    
    async def get_stargate_info(self, stargate_id: int) -> Optional[Dict]:
        """Get stargate information including destination."""
        url = f"{ESI_BASE_URL}/universe/stargates/{stargate_id}/"
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    logger.warning(f"Failed to fetch stargate {stargate_id}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching stargate {stargate_id}: {e}")
            return None


def filter_warzone_systems(fw_systems: List[Dict]) -> List[Dict]:
    """Filter systems to only include Minmatar/Amarr warzone."""
    warzone_systems = []
    
    for system in fw_systems:
        occupier_faction_id = system.get('occupier_faction_id')
        owner_faction_id = system.get('owner_faction_id')
        
        # Include if either occupier or owner is Minmatar or Amarr
        if (occupier_faction_id in [MINMATAR_FACTION_ID, AMARR_FACTION_ID] or 
            owner_faction_id in [MINMATAR_FACTION_ID, AMARR_FACTION_ID]):
            warzone_systems.append(system)
    
    return warzone_systems


async def build_adjacency_map(client: ESIClient, warzone_systems: List[Dict]) -> Dict[int, List[int]]:
    """Build adjacency map for warzone systems."""
    adjacency_map = {}
    warzone_system_ids = {system['solar_system_id'] for system in warzone_systems}
    
    logger.info(f"Building adjacency map for {len(warzone_system_ids)} warzone systems")
    
    for i, system in enumerate(warzone_systems):
        system_id = system['solar_system_id']
        logger.info(f"Processing system {i+1}/{len(warzone_systems)}: {system_id}")
        
        # Get system info to get stargates
        system_info = await client.get_system_info(system_id)
        if not system_info:
            logger.warning(f"Could not fetch info for system {system_id}")
            continue
            
        system_name = system_info.get('name', f'System_{system_id}')
        stargates = system_info.get('stargates', [])
        
        logger.info(f"  System: {system_name} has {len(stargates)} stargates")
        
        adjacent_systems = []
        
        # Process each stargate
        for stargate_id in stargates:
            stargate_info = await client.get_stargate_info(stargate_id)
            if not stargate_info:
                logger.warning(f"  Could not fetch stargate {stargate_id}")
                continue
                
            destination = stargate_info.get('destination', {})
            dest_system_id = destination.get('system_id')
            
            if dest_system_id:
                # Only include connections to other warzone systems
                if dest_system_id in warzone_system_ids:
                    adjacent_systems.append(dest_system_id)
                    logger.debug(f"    -> Connected to warzone system {dest_system_id}")
                else:
                    logger.debug(f"    -> Connected to non-warzone system {dest_system_id} (skipped)")
        
        adjacency_map[system_id] = sorted(adjacent_systems)
        logger.info(f"  {system_name} ({system_id}) connected to {len(adjacent_systems)} warzone systems")
        
        # Add a small delay to be nice to the API
        await asyncio.sleep(0.1)
    
    return adjacency_map


def calculate_frontline_classifications(
    adjacency_map: Dict[int, List[int]], 
    warzone_systems: List[Dict]
) -> Dict[int, str]:
    """
    Calculate frontline classifications based on system ownership and adjacency.
    
    Rules:
    - Frontline: Adjacent to an enemy-controlled system
    - Command Operations: Adjacent to a Frontline system
    - Rearguard: Everything else
    """
    # Create ownership map
    ownership_map = {}
    for system in warzone_systems:
        system_id = system['solar_system_id']
        occupier_faction_id = system.get('occupier_faction_id')
        ownership_map[system_id] = occupier_faction_id
    
    classifications = {}
    
    # First pass: Identify frontline systems
    frontline_systems = set()
    for system_id, adjacent_systems in adjacency_map.items():
        system_faction = ownership_map.get(system_id)
        
        # Check if adjacent to enemy system
        is_frontline = False
        for adjacent_id in adjacent_systems:
            adjacent_faction = ownership_map.get(adjacent_id)
            
            # If adjacent system is controlled by enemy faction, this is frontline
            if (system_faction == MINMATAR_FACTION_ID and adjacent_faction == AMARR_FACTION_ID) or \
               (system_faction == AMARR_FACTION_ID and adjacent_faction == MINMATAR_FACTION_ID):
                is_frontline = True
                break
        
        if is_frontline:
            classifications[system_id] = "frontline"
            frontline_systems.add(system_id)
    
    # Second pass: Identify command operations (adjacent to frontline)
    command_ops_systems = set()
    for system_id, adjacent_systems in adjacency_map.items():
        if system_id in frontline_systems:
            continue  # Already classified as frontline
            
        # Check if adjacent to frontline system
        is_command_ops = False
        for adjacent_id in adjacent_systems:
            if adjacent_id in frontline_systems:
                is_command_ops = True
                break
        
        if is_command_ops:
            classifications[system_id] = "command_operations"
            command_ops_systems.add(system_id)
    
    # Third pass: Everything else is rearguard
    for system_id in adjacency_map.keys():
        if system_id not in classifications:
            classifications[system_id] = "rearguard"
    
    # Log statistics
    frontline_count = len(frontline_systems)
    command_ops_count = len(command_ops_systems)
    rearguard_count = len(adjacency_map) - frontline_count - command_ops_count
    
    logger.info(f"Classification results:")
    logger.info(f"  Frontline: {frontline_count} systems")
    logger.info(f"  Command Operations: {command_ops_count} systems")
    logger.info(f"  Rearguard: {rearguard_count} systems")
    
    return classifications


async def main():
    """Main function to generate system adjacency data."""
    logger.info("Starting system adjacency generation")
    
    async with ESIClient() as client:
        # Get all faction warfare systems
        logger.info("Fetching faction warfare systems...")
        fw_systems = await client.get_faction_warfare_systems()
        if not fw_systems:
            logger.error("Failed to fetch faction warfare systems")
            return
        
        # Filter to warzone systems
        warzone_systems = filter_warzone_systems(fw_systems)
        logger.info(f"Found {len(warzone_systems)} systems in Minmatar/Amarr warzone")
        
        # Build adjacency map
        logger.info("Building adjacency map...")
        adjacency_map = await build_adjacency_map(client, warzone_systems)
        
        # Calculate frontline classifications
        logger.info("Calculating frontline classifications...")
        classifications = calculate_frontline_classifications(adjacency_map, warzone_systems)
        
        # Create system info map for reference
        system_info_map = {}
        for system in warzone_systems:
            system_id = system['solar_system_id']
            system_info = await client.get_system_info(system_id)
            system_name = system_info.get('name', f'System_{system_id}') if system_info else f'System_{system_id}'
            
            system_info_map[system_id] = {
                "name": system_name,
                "occupier_faction_id": system.get('occupier_faction_id'),
                "owner_faction_id": system.get('owner_faction_id'),
                "contested": system.get('contested', 0)
            }
        
        # Prepare output data
        output_data = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "total_systems": len(warzone_systems),
                "frontline_systems": len([c for c in classifications.values() if c == "frontline"]),
                "command_operations_systems": len([c for c in classifications.values() if c == "command_operations"]),
                "rearguard_systems": len([c for c in classifications.values() if c == "rearguard"]),
                "description": "System adjacency and frontline classification data for Minmatar/Amarr warzone"
            },
            "adjacency_map": adjacency_map,
            "classifications": classifications,
            "system_info": system_info_map
        }
        
        # Save to file
        output_path = Path(__file__).parent.parent / "data" / "system_adjacency.json"
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2, sort_keys=True)
        
        logger.info(f"System adjacency data saved to: {output_path}")
        logger.info("Generation complete!")


if __name__ == "__main__":
    asyncio.run(main())
