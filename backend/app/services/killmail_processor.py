import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from collections import defaultdict

from ..models.killmail import (
    Killmail,
    KillmailAttacker,
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
            
            # Fetch full killmail details from ESI API
            # Zkillboard only provides basic metadata, we need ESI for entity details
            full_killmail = None
            try:
                full_killmail = await self.esi_client.get_killmail_details(killmail_id, killmail_hash)
            except Exception as e:
                logger.warning(f"Could not fetch full killmail details for {killmail_id}: {e}")
            
            # Extract victim and attacker information from full killmail data
            if full_killmail:
                victim = full_killmail.get('victim', {})
                victim_character_id = victim.get('character_id')
                victim_corporation_id = victim.get('corporation_id')
                victim_alliance_id = victim.get('alliance_id')
                victim_faction_id = victim.get('faction_id')
                victim_ship_type_id = victim.get('ship_type_id')
                
                # Process ALL attackers, not just final blow
                attackers = full_killmail.get('attackers', [])
                logger.info(f"Processing {len(attackers)} attackers for killmail {killmail_id}")
                
                # Find final blow attacker for main killmail record
                final_blow_attacker = next((a for a in attackers if a.get('final_blow')), {})
                attacker_character_id = final_blow_attacker.get('character_id')
                attacker_corporation_id = final_blow_attacker.get('corporation_id')
                attacker_alliance_id = final_blow_attacker.get('alliance_id')
                attacker_faction_id = final_blow_attacker.get('faction_id')
            else:
                # Fallback to Zkillboard data (likely to be incomplete)
                logger.warning(f"No ESI data for killmail {killmail_id}, using Zkillboard fallback")
                victim = killmail_data.get('victim', {})
                victim_character_id = victim.get('character_id')
                victim_corporation_id = victim.get('corporation_id')
                victim_alliance_id = victim.get('alliance_id')
                victim_faction_id = victim.get('faction_id')
                victim_ship_type_id = victim.get('ship_type_id')
                
                # Extract attacker information (final blow only from Zkillboard)
                attackers = killmail_data.get('attackers', [])
                final_blow_attacker = next((a for a in attackers if a.get('final_blow')), {})
                attacker_character_id = final_blow_attacker.get('character_id')
                attacker_corporation_id = final_blow_attacker.get('corporation_id')
                attacker_alliance_id = final_blow_attacker.get('alliance_id')
                attacker_faction_id = final_blow_attacker.get('faction_id')
            
            # Create/update entity records for victim (in dependency order: Alliance → Corporation → Player)
            self._ensure_alliance_exists(victim_alliance_id, db)
            self._ensure_corporation_exists(victim_corporation_id, victim_alliance_id, db)
            self._ensure_player_exists(victim_character_id, victim_corporation_id, victim_alliance_id, db)
            
            # Create/update entity records for ALL attackers (if we have ESI data)
            if full_killmail:
                for attacker in attackers:
                    att_char_id = attacker.get('character_id')
                    att_corp_id = attacker.get('corporation_id')
                    att_alliance_id = attacker.get('alliance_id')
                    
                    # Create entities in dependency order: Alliance → Corporation → Player
                    self._ensure_alliance_exists(att_alliance_id, db)
                    self._ensure_corporation_exists(att_corp_id, att_alliance_id, db)
                    self._ensure_player_exists(att_char_id, att_corp_id, att_alliance_id, db)
            else:
                # Fallback: only create entities for final blow attacker (in dependency order)
                self._ensure_alliance_exists(attacker_alliance_id, db)
                self._ensure_corporation_exists(attacker_corporation_id, attacker_alliance_id, db)
                self._ensure_player_exists(attacker_character_id, attacker_corporation_id, attacker_alliance_id, db)
            
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
            db.flush()  # Flush to get the killmail_id for foreign key references
            
            # Create individual attacker records for all attackers (if we have ESI data)
            if full_killmail:
                attackers = full_killmail.get('attackers', [])
                for attacker in attackers:
                    attacker_record = KillmailAttacker(
                        killmail_id=killmail_id,
                        character_id=attacker.get('character_id'),
                        corporation_id=attacker.get('corporation_id'),
                        alliance_id=attacker.get('alliance_id'),
                        faction_id=attacker.get('faction_id'),
                        damage_done=attacker.get('damage_done', 0),
                        final_blow=attacker.get('final_blow', False),
                        security_status=attacker.get('security_status'),
                        ship_type_id=attacker.get('ship_type_id'),
                        weapon_type_id=attacker.get('weapon_type_id')
                    )
                    db.add(attacker_record)
                
                logger.info(f"Created {len(attackers)} attacker records for killmail {killmail_id}")
            
            db.commit()
            
            logger.debug(f"Stored killmail {killmail_id} for system {system_id}")
            return killmail_record
            
        except Exception as e:
            logger.error(f"Error processing killmail: {e}")
            db.rollback()
            return None
    
    def _ensure_player_exists(
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
        
        # Use character ID as fallback name for now (ESI calls can be added later via background job)
        character_name = f"Character_{character_id}"
        
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
    
    def _ensure_corporation_exists(
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
        
        # Use corporation ID as fallback name for now (ESI calls can be added later via background job)
        corporation_name = f"Corporation_{corporation_id}"
        ticker = f"C{corporation_id}"
        
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
    
    def _ensure_alliance_exists(
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
        
        # Use alliance ID as fallback name for now (ESI calls can be added later via background job)
        alliance_name = f"Alliance_{alliance_id}"
        ticker = f"A{alliance_id}"
        
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
    
    def get_top_players(
        self,
        system_id: int,
        db: Session,
        limit: int = 10,
        time_window_hours: int = 24
    ) -> List[Dict]:
        """Get most active players in a system"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)
        
        # Query player activity using attacker records (counts all attackers, not just final blow)
        player_stats = db.query(
            Player.character_id,
            Player.character_name,
            func.count(KillmailAttacker.id).label('kills'),
            func.sum(Killmail.total_value).label('isk_killed')
        ).join(
            KillmailAttacker, Player.character_id == KillmailAttacker.character_id
        ).join(
            Killmail, KillmailAttacker.killmail_id == Killmail.killmail_id
        ).filter(
            and_(
                Killmail.system_id == system_id,
                Killmail.timestamp >= start_time,
                Killmail.timestamp <= end_time,
                KillmailAttacker.character_id.isnot(None)  # Filter out NULL attackers
            )
        ).group_by(
            Player.character_id, Player.character_name
        ).order_by(
            func.count(KillmailAttacker.id).desc()
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
    
    def get_top_corporations(
        self,
        system_id: int,
        db: Session,
        limit: int = 10,
        time_window_hours: int = 24
    ) -> List[Dict]:
        """Get most active corporations in a system"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)
        
        # Query corporation activity using attacker records (counts all attackers, not just final blow)
        corp_stats = db.query(
            Corporation.corporation_id,
            Corporation.corporation_name,
            Corporation.ticker,
            func.count(KillmailAttacker.id).label('kills'),
            func.sum(Killmail.total_value).label('isk_killed'),
            func.count(func.distinct(KillmailAttacker.character_id)).label('unique_players')
        ).join(
            KillmailAttacker, Corporation.corporation_id == KillmailAttacker.corporation_id
        ).join(
            Killmail, KillmailAttacker.killmail_id == Killmail.killmail_id
        ).filter(
            and_(
                Killmail.system_id == system_id,
                Killmail.timestamp >= start_time,
                Killmail.timestamp <= end_time,
                KillmailAttacker.corporation_id.isnot(None)  # Filter out NULL attackers
            )
        ).group_by(
            Corporation.corporation_id, Corporation.corporation_name, Corporation.ticker
        ).order_by(
            func.count(KillmailAttacker.id).desc()
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
    
    def get_top_alliances(
        self,
        system_id: int,
        db: Session,
        limit: int = 10,
        time_window_hours: int = 24
    ) -> List[Dict]:
        """Get most active alliances in a system"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_window_hours)
        
        # Query alliance activity using attacker records (counts all attackers, not just final blow)
        alliance_stats = db.query(
            Alliance.alliance_id,
            Alliance.alliance_name,
            Alliance.ticker,
            func.count(KillmailAttacker.id).label('kills'),
            func.sum(Killmail.total_value).label('isk_killed'),
            func.count(func.distinct(KillmailAttacker.character_id)).label('unique_players'),
            func.count(func.distinct(KillmailAttacker.corporation_id)).label('unique_corporations')
        ).join(
            KillmailAttacker, Alliance.alliance_id == KillmailAttacker.alliance_id
        ).join(
            Killmail, KillmailAttacker.killmail_id == Killmail.killmail_id
        ).filter(
            and_(
                Killmail.system_id == system_id,
                Killmail.timestamp >= start_time,
                Killmail.timestamp <= end_time,
                KillmailAttacker.alliance_id.isnot(None)  # Filter out NULL attackers
            )
        ).group_by(
            Alliance.alliance_id, Alliance.alliance_name, Alliance.ticker
        ).order_by(
            func.count(KillmailAttacker.id).desc()
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
