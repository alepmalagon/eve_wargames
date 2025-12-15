import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)


class ZkillboardClient:
    """
    Client for interacting with the Zkillboard API.
    
    Implements proper rate limiting and error handling according to Zkillboard API guidelines:
    - 30 seconds minimum between requests
    - Proper User-Agent header
    - gzip compression
    - Maximum 1000 killmails per request
    """
    
    def __init__(self):
        self.base_url = "https://zkillboard.com/api"
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_time = 0
        self.min_request_interval = 30  # 30 seconds between requests
        
        # Headers as required by Zkillboard API
        self.headers = {
            'User-Agent': 'EVE Wargames Analytics - alepmalagon@gmail.com - https://github.com/alepmalagon/eve_wargames',
            'Accept-Encoding': 'gzip',
            'Accept': 'application/json'
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=60)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _rate_limit(self):
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            logger.info(f"Rate limiting: sleeping for {sleep_time:.1f} seconds")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def _make_request(self, url: str, max_retries: int = 3) -> List[Dict]:
        """
        Make a request to Zkillboard API with retries and error handling
        
        Args:
            url: Full URL to request
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of killmail dictionaries
        """
        await self._ensure_session()
        await self._rate_limit()
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Making request to: {url} (attempt {attempt + 1})")
                
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Successfully fetched {len(data)} killmails")
                        return data
                    elif response.status == 429:
                        # Rate limited - wait longer
                        wait_time = 60 * (attempt + 1)
                        logger.warning(f"Rate limited (429), waiting {wait_time} seconds")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status == 404:
                        # No data available
                        logger.info("No killmail data available (404)")
                        return []
                    else:
                        logger.error(f"HTTP {response.status}: {await response.text()}")
                        if attempt == max_retries:
                            raise Exception(f"HTTP {response.status} after {max_retries} retries")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Request timeout (attempt {attempt + 1})")
                if attempt == max_retries:
                    raise Exception("Request timeout after retries")
                await asyncio.sleep(5 * (attempt + 1))
                
            except Exception as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                if attempt == max_retries:
                    raise
                await asyncio.sleep(5 * (attempt + 1))
        
        return []
    
    async def get_system_kills(
        self, 
        system_id: int, 
        past_hours: int = 24,
        page: int = 1
    ) -> List[Dict]:
        """
        Fetch killmails for a specific system
        
        Args:
            system_id: EVE Online system ID
            past_hours: Number of hours to look back (max 168 = 7 days)
            page: Page number for pagination
            
        Returns:
            List of killmail dictionaries
        """
        # Convert hours to seconds (must be multiple of 3600 per API docs)
        past_seconds = min(past_hours * 3600, 604800)  # Max 7 days
        past_seconds = (past_seconds // 3600) * 3600  # Round to nearest hour
        
        # Build URL according to Zkillboard API format
        url = f"{self.base_url}/kills/systemID/{system_id}/pastSeconds/{past_seconds}/"
        
        if page > 1:
            url += f"page/{page}/"
        
        return await self._make_request(url)
    
    async def get_system_losses(
        self, 
        system_id: int, 
        past_hours: int = 24,
        page: int = 1
    ) -> List[Dict]:
        """
        Fetch losses for a specific system
        
        Args:
            system_id: EVE Online system ID
            past_hours: Number of hours to look back (max 168 = 7 days)
            page: Page number for pagination
            
        Returns:
            List of killmail dictionaries
        """
        # Convert hours to seconds (must be multiple of 3600 per API docs)
        past_seconds = min(past_hours * 3600, 604800)  # Max 7 days
        past_seconds = (past_seconds // 3600) * 3600  # Round to nearest hour
        
        # Build URL according to Zkillboard API format
        url = f"{self.base_url}/losses/systemID/{system_id}/pastSeconds/{past_seconds}/"
        
        if page > 1:
            url += f"page/{page}/"
        
        return await self._make_request(url)
    
    async def get_system_all_activity(
        self, 
        system_id: int, 
        past_hours: int = 24,
        max_pages: int = 5
    ) -> List[Dict]:
        """
        Fetch all killmail activity (kills + losses) for a system
        
        Args:
            system_id: EVE Online system ID
            past_hours: Number of hours to look back
            max_pages: Maximum pages to fetch (to prevent infinite loops)
            
        Returns:
            List of all killmail dictionaries
        """
        all_killmails = []
        
        # Get both kills and losses
        for endpoint_type in ['kills', 'losses']:
            page = 1
            while page <= max_pages:
                if endpoint_type == 'kills':
                    killmails = await self.get_system_kills(system_id, past_hours, page)
                else:
                    killmails = await self.get_system_losses(system_id, past_hours, page)
                
                if not killmails:
                    break
                
                all_killmails.extend(killmails)
                
                # If we got less than 1000 killmails, we've reached the end
                if len(killmails) < 1000:
                    break
                
                page += 1
        
        # Remove duplicates based on killmail_id
        seen_ids = set()
        unique_killmails = []
        for km in all_killmails:
            if km.get('killmail_id') not in seen_ids:
                seen_ids.add(km.get('killmail_id'))
                unique_killmails.append(km)
        
        logger.info(f"Fetched {len(unique_killmails)} unique killmails for system {system_id}")
        return unique_killmails
    
    async def get_faction_kills(
        self,
        faction_id: int,
        past_hours: int = 24,
        page: int = 1
    ) -> List[Dict]:
        """
        Fetch kills by faction (500002 = Minmatar, 500003 = Amarr)
        
        Args:
            faction_id: Faction ID (500002 or 500003)
            past_hours: Number of hours to look back
            page: Page number for pagination
            
        Returns:
            List of killmail dictionaries
        """
        past_seconds = min(past_hours * 3600, 604800)  # Max 7 days
        past_seconds = (past_seconds // 3600) * 3600  # Round to nearest hour
        
        url = f"{self.base_url}/kills/factionID/{faction_id}/pastSeconds/{past_seconds}/"
        
        if page > 1:
            url += f"page/{page}/"
        
        return await self._make_request(url)
    
    def extract_killmail_data(self, killmail: Dict) -> Dict:
        """
        Extract relevant data from a Zkillboard killmail response
        
        Args:
            killmail: Raw killmail dictionary from Zkillboard API
            
        Returns:
            Processed killmail data dictionary
        """
        try:
            # Extract basic killmail info
            killmail_id = killmail.get('killmail_id')
            killmail_hash = killmail.get('zkb', {}).get('hash')
            total_value = killmail.get('zkb', {}).get('totalValue', 0.0)
            points = killmail.get('zkb', {}).get('points', 0)
            
            # Parse timestamp
            timestamp_str = killmail.get('killmail_time')
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')) if timestamp_str else datetime.utcnow()
            
            # Extract victim information
            victim = killmail.get('victim', {})
            victim_character_id = victim.get('character_id')
            victim_corporation_id = victim.get('corporation_id')
            victim_alliance_id = victim.get('alliance_id')
            victim_faction_id = victim.get('faction_id')
            victim_ship_type_id = victim.get('ship_type_id')
            
            # Extract attacker information (final blow)
            attackers = killmail.get('attackers', [])
            final_blow_attacker = next((a for a in attackers if a.get('final_blow')), {})
            
            attacker_character_id = final_blow_attacker.get('character_id')
            attacker_corporation_id = final_blow_attacker.get('corporation_id')
            attacker_alliance_id = final_blow_attacker.get('alliance_id')
            attacker_faction_id = final_blow_attacker.get('faction_id')
            
            return {
                'killmail_id': killmail_id,
                'killmail_hash': killmail_hash,
                'timestamp': timestamp,
                'total_value': total_value,
                'points': points,
                'victim_character_id': victim_character_id,
                'victim_corporation_id': victim_corporation_id,
                'victim_alliance_id': victim_alliance_id,
                'victim_faction_id': victim_faction_id,
                'victim_ship_type_id': victim_ship_type_id,
                'attacker_character_id': attacker_character_id,
                'attacker_corporation_id': attacker_corporation_id,
                'attacker_alliance_id': attacker_alliance_id,
                'attacker_faction_id': attacker_faction_id,
                'system_id': killmail.get('solar_system_id')
            }
            
        except Exception as e:
            logger.error(f"Error extracting killmail data: {e}")
            return None
