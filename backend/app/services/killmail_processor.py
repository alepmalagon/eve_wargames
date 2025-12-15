import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from collections import defaultdict

from ..models.killmail import (
    Killmail,
    Player,
    Corporation,
    Alliance,
    SystemKillStats,
    PlayerKillStats,
    CorporationKillStats,
    AllianceKillStats
)
from ..models.system import System
from .esi_client import ESIClient

logger = logging.getLogger(__name__)


class KillmailProcessor:
    """
    Service for processing and storing killmail data from Zkillboard API.
    
    Handles:
    - Parsing raw killmail data
    - Creating/updating player, corporation, alliance records
    - Storing individual killmails
    - Calculating and storing aggregated statistics
    """
    
    def __init__(self, esi_client: Optional[ESIClient] = None):
        self.esi_client = esi_client or ESIClient()
        self.faction_ids = {500002, 500003}  # Minmatar and Amarr
    
    async def process_system_killmails(
        self,
        system_id: int,
        killmails: List[Dict],
        db: Session
    ) -> Dict:
        """
        Process killmails for a system and store in database
        
        Args:
            system_id: System ID to process killmails for
            killmails: List of raw killmail dictionaries from Zkillboard
            db: Database session
            
        Returns:
            Dictionary with processing statistics
        """
        logger.info(f"Processing {len(killmails)} killmails for system {system_id}")
        
        stats = {
            'killmails_processed': 0,
            'killmails_stored': 0,
            'killmails_skipped': 0,
            'players_created': 0,
            'corporations_created': 0,
            'alliances_created': 0,
            'errors': 0
        }
        
        for killmail_data in killmails:
            try:
                # Extract and validate killmail data
                processed_km = await self._process_single_killmail(killmail_data, system_id, db)
                
                if processed_km:
                    stats['killmails_stored'] += 1
                else:
                    stats['killmails_skipped'] += 1
                    
                stats['killmails_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing killmail {killmail_data.get('killmail_id')}: {e}")
                stats['errors'] += 1
        
        # Update aggregated statistics
        await self._update_system_kill_stats(system_id, db)
        
        logger.info(f"Completed processing for system {system_id}: {stats}")
        return stats
    
    async def _process_single_killmail(
        self,
        killmail_data: Dict,
        system_id: int,
        db: Session
    ) -> Optional[Killmail]:
        """
        Process a single killmail and store it in the database
        
        Args:
            killmail_data: Raw killmail data from Zkillboard
            system_id: System ID where the kill occurred
            db: Database session
            
        Returns:
            Created Killmail or None if skipped
        """
        try:
            killmail_id = killmail_data.get('killmail_id')
            killmail_hash = killmail_data.get('zkb', {}).get('hash')
            
            if not killmail_id or not killmail_hash:
                logger.warning("Killmail missing ID or hash, skipping")
                return None
            
            # Check if killmail already exists
            existing = db.query(Killmail).filter_by(killmail_id=killmail_id).first()
            if existing:
                logger.debug(f"Killmail {killmail_id} already exists, skipping")
                return existing
            
            # Extract killmail data
            total_value = killmail_data.get('zkb', {}).get('totalValue', 0.0)
            points = killmail_data.get('zkb', {}).get('points', 0)
            
            # Parse timestamp
            timestamp_str = killmail_data.get('killmail_time')
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.utcnow()
            
            # Extract victim information
            victim = killmail_data.get('victim', {})
            victim_character_id = victim.get('character_id')
            victim_corporation_id = victim.get('corporation_id')
            victim_alliance_id = victim.get('alliance_id')
            victim_faction_id = victim.get('faction_id')
            victim_ship_type_id = victim.get('ship_type_id')
            
            # Extract attacker information (final blow)
            attackers = killmail_data.get('attackers', [])
            final_blow_attacker = next((a for a in attackers if a.get('final_blow')), {})
            
            attacker_character_id = final_blow_attacker.get('character_id')
            attacker_corporation_id = final_blow_attacker.get('corporation_id')
            attacker_alliance_id = final_blow_attacker.get('alliance_id')
            attacker_faction_id = final_blow_attacker.get('faction_id')
            
            # Create/update entity records
            await self._ensure_player_exists(victim_character_id, victim_corporation_id, victim_alliance_id, db)
            await self._ensure_player_exists(attacker_character_id, attacker_corporation_id, attacker_alliance_id, db)
            await self._ensure_corporation_exists(victim_corporation_id, victim_alliance_id, db)
            await self._ensure_corporation_exists(attacker_corporation_id, attacker_alliance_id, db)
            await self._ensure_alliance_exists(victim_alliance_id, db)
            await self._ensure_alliance_exists(attacker_alliance_id, db)
            
            # Create killmail record
            killmail_record = Killmail(
                killmail_id=killmail_id,
                killmail_hash=killmail_hash,
                system_id=system_id,
                timestamp=timestamp,
                total_value=total_value,
                points=points,
                victim_character_id=victim_character_id,
                victim_corporation_id=victim_corporation_id,
                victim_alliance_id=victim_alliance_id,
                victim_faction_id=victim_faction_id,
                victim_ship_type_id=victim_ship_type_id,
                attacker_character_id=attacker_character_id,
                attacker_corporation_id=attacker_corporation_id,
                attacker_alliance_id=attacker_alliance_id,
                attacker_faction_id=attacker_faction_id
            )
            
            db.add(killmail_record)
            db.commit()
            
            logger.debug(f"Stored killmail {killmail_id} for system {system_id}")
            return killmail_record
            
        except Exception as e:
            logger.error(f"Error processing killmail: {e}")
            db.rollback()
            return None
    
    async def _ensure_player_exists(
        self,
        character_id: Optional[int],
        corporation_id: Optional[int],
        alliance_id: Optional[int],
        db: Session
    ) -> Optional[Player]:
        """Ensure player record exists in database"""
        if not character_id:
            return None
        
        player = db.query(Player).filter_by(character_id=character_id).first()
        if player:
            # Update corporation/alliance if changed
            if player.corporation_id != corporation_id or player.alliance_id != alliance_id:
                player.corporation_id = corporation_id
                player.alliance_id = alliance_id
                db.commit()
            return player
        
        # Get character name from ESI
        character_name = f"Character_{character_id}"  # Default fallback
        try:
            character_info = await self.esi_client.get_character_info(character_id)
            if character_info:
                character_name = character_info.get('name', character_name)
        except Exception as e:
            logger.warning(f"Could not fetch character name for {character_id}: {e}")
        
        # Create new player record
        player = Player(
            character_id=character_id,
            character_name=character_name,
            corporation_id=corporation_id,
            alliance_id=alliance_id
        )
        
        db.add(player)
        db.commit()
        logger.debug(f"Created player record: {character_name} ({character_id})")
        return player
    
    async def _ensure_corporation_exists(
        self,
        corporation_id: Optional[int],
        alliance_id: Optional[int],
        db: Session
    ) -> Optional[Corporation]:
        """Ensure corporation record exists in database"""
        if not corporation_id:
            return None
        
        corporation = db.query(Corporation).filter_by(corporation_id=corporation_id).first()
        if corporation:
            # Update alliance if changed
            if corporation.alliance_id != alliance_id:
                corporation.alliance_id = alliance_id
                db.commit()
            return corporation
        
        # Get corporation info from ESI
        corporation_name = f"Corporation_{corporation_id}"  # Default fallback
        ticker = ""
        try:
            corp_info = await self.esi_client.get_corporation_info(corporation_id)
            if corp_info:
                corporation_name = corp_info.get('name', corporation_name)
                ticker = corp_info.get('ticker', '')
        except Exception as e:
            logger.warning(f"Could not fetch corporation info for {corporation_id}: {e}")
        
        # Create new corporation record
        corporation = Corporation(
            corporation_id=corporation_id,
            corporation_name=corporation_name,
            alliance_id=alliance_id,
            ticker=ticker
        )
        
        db.add(corporation)
        db.commit()
        logger.debug(f"Created corporation record: {corporation_name} ({corporation_id})")
        return corporation
    
    async def _ensure_alliance_exists(
        self,
        alliance_id: Optional[int],
        db: Session
    ) -> Optional[Alliance]:
        """Ensure alliance record exists in database"""
        if not alliance_id:
            return None
        
        alliance = db.query(Alliance).filter_by(alliance_id=alliance_id).first()
        if alliance:
            return alliance
        
        # Get alliance info from ESI
        alliance_name = f"Alliance_{alliance_id}"  # Default fallback
        ticker = ""
        try:
            alliance_info = await self.esi_client.get_alliance_info(alliance_id)
            if alliance_info:
                alliance_name = alliance_info.get('name', alliance_name)
                ticker = alliance_info.get('ticker', '')
        except Exception as e:
            logger.warning(f"Could not fetch alliance info for {alliance_id}: {e}")
        
        # Create new alliance record
        alliance = Alliance(
            alliance_id=alliance_id,
            alliance_name=alliance_name,
            ticker=ticker
        )
        
        db.add(alliance)
        db.commit()
        logger.debug(f"Created alliance record: {alliance_name} ({alliance_id})")
        return alliance
    
    async def _update_system_kill_stats(
        self,
        system_id: int,
        db: Session,
        time_window_hours: int = 24
    ) -> SystemKillStats:
        """
        Calculate and update aggregated kill statistics for a system
        
        Args:
            system_id: System ID to calculate stats for
            db: Database session
            time_window_hours: Time window for statistics calculation
            
        Returns:
            Updated SystemKillStats record
        """
        logger.info(f"Updating kill statistics for system {system_id}")
        
        # Calculate time window
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)
        
        # Query killmails in time window
        killmails = db.query(Killmail).filter(
            and_(
                Killmail.system_id == system_id,
                Killmail.timestamp >= start_time,
                Killmail.timestamp <= end_time
            )
        ).all()
        
        # Calculate statistics
        total_kills = len(killmails)
        total_isk_value = sum(km.total_value for km in killmails)
        
        # Faction-specific statistics
        minmatar_kills = len([km for km in killmails if km.attacker_faction_id == 500002])
        minmatar_losses = len([km for km in killmails if km.victim_faction_id == 500002])
        minmatar_isk_killed = sum(km.total_value for km in killmails if km.attacker_faction_id == 500002)
        minmatar_isk_lost = sum(km.total_value for km in killmails if km.victim_faction_id == 500002)
        
        amarr_kills = len([km for km in killmails if km.attacker_faction_id == 500003])
        amarr_losses = len([km for km in killmails if km.victim_faction_id == 500003])
        amarr_isk_killed = sum(km.total_value for km in killmails if km.attacker_faction_id == 500003)
        amarr_isk_lost = sum(km.total_value for km in killmails if km.victim_faction_id == 500003)
        
        # Unique entity counts
        unique_players = len(set(
            [km.victim_character_id for km in killmails if km.victim_character_id] +
            [km.attacker_character_id for km in killmails if km.attacker_character_id]
        ))
        
        unique_corporations = len(set(
            [km.victim_corporation_id for km in killmails if km.victim_corporation_id] +
            [km.attacker_corporation_id for km in killmails if km.attacker_corporation_id]
        ))
        
        unique_alliances = len(set(
            [km.victim_alliance_id for km in killmails if km.victim_alliance_id] +
            [km.attacker_alliance_id for km in killmails if km.attacker_alliance_id]
        ))
        
        # Create or update system kill stats
        stats = SystemKillStats(
            system_id=system_id,
            timestamp=end_time,
            time_window_hours=time_window_hours,
            total_kills=total_kills,
            total_isk_value=total_isk_value,
            minmatar_kills=minmatar_kills,
            minmatar_losses=minmatar_losses,
            minmatar_isk_killed=minmatar_isk_killed,
            minmatar_isk_lost=minmatar_isk_lost,
            amarr_kills=amarr_kills,
            amarr_losses=amarr_losses,
            amarr_isk_killed=amarr_isk_killed,
            amarr_isk_lost=amarr_isk_lost,
            unique_players=unique_players,
            unique_corporations=unique_corporations,
            unique_alliances=unique_alliances
        )
        
        db.add(stats)
        db.commit()
        
        logger.info(f"Updated system {system_id} stats: {total_kills} kills, {total_isk_value:,.0f} ISK")
        return stats
    
    async def get_top_players(
        self,
        system_id: int,
        db: Session,
        limit: int = 10,
        time_window_hours: int = 24
    ) -> List[Dict]:
        """Get most active players in a system"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)
        
        # Query player activity
        player_stats = db.query(
            Player.character_id,
            Player.character_name,
            func.count(Killmail.killmail_id).label('kills'),
            func.sum(Killmail.total_value).label('isk_killed')
        ).join(
            Killmail, Player.character_id == Killmail.attacker_character_id
        ).filter(
            and_(
                Killmail.system_id == system_id,
                Killmail.timestamp >= start_time,
                Killmail.timestamp <= end_time
            )
        ).group_by(
            Player.character_id, Player.character_name
        ).order_by(
            func.count(Killmail.killmail_id).desc()
        ).limit(limit).all()
        
        return [
            {
                'character_id': stat.character_id,
                'character_name': stat.character_name,
                'kills': stat.kills,
                'isk_killed': stat.isk_killed or 0.0
            }
            for stat in player_stats
        ]
    
    async def get_top_corporations(
        self,
        system_id: int,
        db: Session,
        limit: int = 10,
        time_window_hours: int = 24
    ) -> List[Dict]:
        """Get most active corporations in a system"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)
        
        # Query corporation activity
        corp_stats = db.query(
            Corporation.corporation_id,
            Corporation.corporation_name,
            Corporation.ticker,
            func.count(Killmail.killmail_id).label('kills'),
            func.sum(Killmail.total_value).label('isk_killed'),
            func.count(func.distinct(Killmail.attacker_character_id)).label('unique_players')
        ).join(
            Killmail, Corporation.corporation_id == Killmail.attacker_corporation_id
        ).filter(
            and_(
                Killmail.system_id == system_id,
                Killmail.timestamp >= start_time,
                Killmail.timestamp <= end_time
            )
        ).group_by(
            Corporation.corporation_id, Corporation.corporation_name, Corporation.ticker
        ).order_by(
            func.count(Killmail.killmail_id).desc()
        ).limit(limit).all()
        
        return [
            {
                'corporation_id': stat.corporation_id,
                'corporation_name': stat.corporation_name,
                'ticker': stat.ticker,
                'kills': stat.kills,
                'isk_killed': stat.isk_killed or 0.0,
                'unique_players': stat.unique_players
            }
            for stat in corp_stats
        ]
    
    async def get_top_alliances(
        self,
        system_id: int,
        db: Session,
        limit: int = 10,
        time_window_hours: int = 24
    ) -> List[Dict]:
        """Get most active alliances in a system"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)
        
        # Query alliance activity
        alliance_stats = db.query(
            Alliance.alliance_id,
            Alliance.alliance_name,
            Alliance.ticker,
            func.count(Killmail.killmail_id).label('kills'),
            func.sum(Killmail.total_value).label('isk_killed'),
            func.count(func.distinct(Killmail.attacker_character_id)).label('unique_players'),
            func.count(func.distinct(Killmail.attacker_corporation_id)).label('unique_corporations')
        ).join(
            Killmail, Alliance.alliance_id == Killmail.attacker_alliance_id
        ).filter(
            and_(
                Killmail.system_id == system_id,
                Killmail.timestamp >= start_time,
                Killmail.timestamp <= end_time
            )
        ).group_by(
            Alliance.alliance_id, Alliance.alliance_name, Alliance.ticker
        ).order_by(
            func.count(Killmail.killmail_id).desc()
        ).limit(limit).all()
        
        return [
            {
                'alliance_id': stat.alliance_id,
                'alliance_name': stat.alliance_name,
                'ticker': stat.ticker,
                'kills': stat.kills,
                'isk_killed': stat.isk_killed or 0.0,
                'unique_players': stat.unique_players,
                'unique_corporations': stat.unique_corporations
            }
            for stat in alliance_stats
        ]
