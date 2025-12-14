"""
Data processing service for faction warfare metrics.

This module handles the transformation and storage of ESI data
into the database models for historical analysis.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..models.system import System, SystemSnapshot
from ..models.faction_warfare import FactionWarfareSnapshot
from ..models.faction import Faction

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    Processes and stores faction warfare data from ESI API.
    """
    
    # Faction IDs for Minmatar/Amarr warzone
    MINMATAR_FACTION_ID = 500002
    AMARR_FACTION_ID = 500003
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def process_faction_warfare_data(
        self, 
        fw_systems: List[Dict], 
        fw_stats: Optional[Dict] = None
    ) -> Dict:
        """
        Process faction warfare systems data and store in database.
        
        Args:
            fw_systems: List of faction warfare systems from ESI
            fw_stats: Optional faction warfare statistics from ESI
            
        Returns:
            dict: Processing results and statistics
        """
        try:
            # Filter for Minmatar/Amarr warzone systems
            warzone_systems = self._filter_warzone_systems(fw_systems)
            
            logger.info(f"Processing {len(warzone_systems)} warzone systems")
            
            # Ensure factions exist in database
            self._ensure_factions_exist()
            
            # Process individual systems
            system_results = self._process_systems(warzone_systems)
            
            # Create warzone-wide snapshot
            warzone_snapshot = self._create_warzone_snapshot(warzone_systems, fw_stats)
            
            # Commit all changes
            self.db.commit()
            
            return {
                "systems_processed": len(warzone_systems),
                "snapshots_created": system_results["snapshots_created"],
                "systems_updated": system_results["systems_updated"],
                "warzone_snapshot_created": warzone_snapshot is not None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing faction warfare data: {str(e)}", exc_info=True)
            self.db.rollback()
            raise
    
    def _filter_warzone_systems(self, fw_systems: List[Dict]) -> List[Dict]:
        """
        Filter systems to only include Minmatar/Amarr warzone.
        
        Args:
            fw_systems: All faction warfare systems from ESI
            
        Returns:
            List of systems in the Minmatar/Amarr warzone
        """
        warzone_systems = []
        
        for system in fw_systems:
            occupier_faction_id = system.get('occupier_faction_id')
            owner_faction_id = system.get('owner_faction_id')
            
            # Include systems controlled by or contested between Minmatar/Amarr
            if (occupier_faction_id in [self.MINMATAR_FACTION_ID, self.AMARR_FACTION_ID] or
                owner_faction_id in [self.MINMATAR_FACTION_ID, self.AMARR_FACTION_ID]):
                warzone_systems.append(system)
        
        return warzone_systems
    
    def _ensure_factions_exist(self):
        """Ensure Minmatar and Amarr factions exist in the database."""
        factions_data = [
            {
                "faction_id": self.MINMATAR_FACTION_ID,
                "name": "Minmatar Republic",
                "ticker": "MIN",
                "militia_name": "Tribal Liberation Force"
            },
            {
                "faction_id": self.AMARR_FACTION_ID,
                "name": "Amarr Empire", 
                "ticker": "AMR",
                "militia_name": "Imperial Navy"
            }
        ]
        
        for faction_data in factions_data:
            existing_faction = self.db.query(Faction).filter(
                Faction.faction_id == faction_data["faction_id"]
            ).first()
            
            if not existing_faction:
                faction = Faction(**faction_data)
                self.db.add(faction)
                logger.info(f"Created faction: {faction_data['name']}")
    
    def _process_systems(self, warzone_systems: List[Dict]) -> Dict:
        """
        Process individual systems and create snapshots.
        
        Args:
            warzone_systems: List of warzone systems to process
            
        Returns:
            dict: Processing statistics
        """
        snapshots_created = 0
        systems_updated = 0
        
        for system_data in warzone_systems:
            try:
                system_id = system_data.get('solar_system_id')
                if not system_id:
                    continue
                
                # Get or create system record
                system = self.db.query(System).filter(
                    System.system_id == system_id
                ).first()
                
                if not system:
                    # Create new system record
                    system = System(
                        system_id=system_id,
                        name=f"System_{system_id}",  # Will be updated with actual name later
                        security_status=0.0  # Default security status, will be updated later
                    )
                    self.db.add(system)
                    self.db.flush()  # Get the ID
                
                # Update system current status
                system.controlling_faction_id = system_data.get('occupier_faction_id')
                system.contested = system_data.get('contested', 0)
                system.capture_percent = system_data.get('capture_percent', 0.0)
                system.advantage_percent = system_data.get('advantage_percent', 0.0)
                
                systems_updated += 1
                
                # Create system snapshot
                snapshot = SystemSnapshot(
                    system_id=system_id,
                    controlling_faction_id=system_data.get('occupier_faction_id'),
                    capture_percent=system_data.get('capture_percent', 0.0),
                    advantage_percent=system_data.get('advantage_percent', 0.0),
                    contested=system_data.get('contested', 0),
                    timestamp=datetime.utcnow()
                )
                
                self.db.add(snapshot)
                snapshots_created += 1
                
            except Exception as e:
                logger.error(f"Error processing system {system_data.get('solar_system_id')}: {str(e)}")
                continue
        
        return {
            "snapshots_created": snapshots_created,
            "systems_updated": systems_updated
        }
    
    def _create_warzone_snapshot(
        self, 
        warzone_systems: List[Dict], 
        fw_stats: Optional[Dict] = None
    ) -> Optional[FactionWarfareSnapshot]:
        """
        Create a warzone-wide snapshot with aggregated statistics.
        
        Args:
            warzone_systems: List of warzone systems
            fw_stats: Optional faction warfare statistics from ESI
            
        Returns:
            FactionWarfareSnapshot or None if creation failed
        """
        try:
            # Calculate system control statistics
            minmatar_controlled = 0
            amarr_controlled = 0
            minmatar_contested = 0
            amarr_contested = 0
            total_contested = 0
            
            minmatar_total_capture = 0.0
            amarr_total_capture = 0.0
            minmatar_total_advantage = 0.0
            amarr_total_advantage = 0.0
            
            for system in warzone_systems:
                occupier_faction_id = system.get('occupier_faction_id')
                contested = system.get('contested', 0) == 1
                capture_percent = system.get('capture_percent', 0.0)
                advantage_percent = system.get('advantage_percent', 0.0)
                
                if occupier_faction_id == self.MINMATAR_FACTION_ID:
                    minmatar_controlled += 1
                    minmatar_total_capture += capture_percent
                    minmatar_total_advantage += advantage_percent
                    if contested:
                        minmatar_contested += 1
                        
                elif occupier_faction_id == self.AMARR_FACTION_ID:
                    amarr_controlled += 1
                    amarr_total_capture += capture_percent
                    amarr_total_advantage += advantage_percent
                    if contested:
                        amarr_contested += 1
                
                if contested:
                    total_contested += 1
            
            total_systems = len(warzone_systems)
            
            # Calculate percentages
            minmatar_control_pct = (minmatar_controlled / total_systems * 100) if total_systems > 0 else 0
            amarr_control_pct = (amarr_controlled / total_systems * 100) if total_systems > 0 else 0
            contested_pct = (total_contested / total_systems * 100) if total_systems > 0 else 0
            
            # Calculate average capture/advantage percentages
            minmatar_avg_capture = (minmatar_total_capture / minmatar_controlled) if minmatar_controlled > 0 else 0
            amarr_avg_capture = (amarr_total_capture / amarr_controlled) if amarr_controlled > 0 else 0
            minmatar_avg_advantage = (minmatar_total_advantage / minmatar_controlled) if minmatar_controlled > 0 else 0
            amarr_avg_advantage = (amarr_total_advantage / amarr_controlled) if amarr_controlled > 0 else 0
            
            # Create the snapshot
            snapshot = FactionWarfareSnapshot(
                timestamp=datetime.utcnow(),
                
                # Minmatar statistics
                minmatar_systems_controlled=minmatar_controlled,
                minmatar_systems_contested=minmatar_contested,
                minmatar_total_capture_percent=minmatar_avg_capture,
                minmatar_total_advantage_percent=minmatar_avg_advantage,
                minmatar_control_percentage=minmatar_control_pct,
                
                # Amarr statistics
                amarr_systems_controlled=amarr_controlled,
                amarr_systems_contested=amarr_contested,
                amarr_total_capture_percent=amarr_avg_capture,
                amarr_total_advantage_percent=amarr_avg_advantage,
                amarr_control_percentage=amarr_control_pct,
                
                # Overall warzone statistics
                total_systems=total_systems,
                total_contested_systems=total_contested,
                contested_percentage=contested_pct,
                
                # Kill data (placeholder - would need additional ESI calls or zkillboard integration)
                minmatar_kills_last_24h=0,
                minmatar_losses_last_24h=0,
                minmatar_kills_value_last_24h=0.0,
                minmatar_losses_value_last_24h=0.0,
                amarr_kills_last_24h=0,
                amarr_losses_last_24h=0,
                amarr_kills_value_last_24h=0.0,
                amarr_losses_value_last_24h=0.0,
                total_kills_last_24h=0,
                total_kill_value_last_24h=0.0,
                
                # Activity metrics
                activity_index=total_contested  # Simple activity metric based on contested systems
            )
            
            self.db.add(snapshot)
            
            logger.info(f"Created warzone snapshot: {minmatar_controlled} MIN, {amarr_controlled} AMR, {total_contested} contested")
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error creating warzone snapshot: {str(e)}", exc_info=True)
            return None
    
    def get_latest_trends(self, hours: int = 24) -> Dict:
        """
        Get trend data for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            dict: Trend analysis data
        """
        try:
            from datetime import timedelta
            
            start_time = datetime.utcnow() - timedelta(hours=hours)
            
            snapshots = self.db.query(FactionWarfareSnapshot).filter(
                FactionWarfareSnapshot.timestamp >= start_time
            ).order_by(FactionWarfareSnapshot.timestamp).all()
            
            if len(snapshots) < 2:
                return {"error": "Insufficient data for trend analysis"}
            
            first_snapshot = snapshots[0]
            latest_snapshot = snapshots[-1]
            
            # Calculate changes
            minmatar_system_change = latest_snapshot.minmatar_systems_controlled - first_snapshot.minmatar_systems_controlled
            amarr_system_change = latest_snapshot.amarr_systems_controlled - first_snapshot.amarr_systems_controlled
            contested_change = latest_snapshot.total_contested_systems - first_snapshot.total_contested_systems
            
            return {
                "period_hours": hours,
                "snapshots_count": len(snapshots),
                "changes": {
                    "minmatar_systems": minmatar_system_change,
                    "amarr_systems": amarr_system_change,
                    "contested_systems": contested_change
                },
                "latest": {
                    "minmatar_controlled": latest_snapshot.minmatar_systems_controlled,
                    "amarr_controlled": latest_snapshot.amarr_systems_controlled,
                    "contested": latest_snapshot.total_contested_systems,
                    "timestamp": latest_snapshot.timestamp.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating trends: {str(e)}", exc_info=True)
            return {"error": str(e)}
