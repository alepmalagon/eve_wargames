"""
EVE Online ESI API client for fetching faction warfare data.

Handles authentication, rate limiting, and data fetching from the ESI API.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import httpx
import redis
import json
from cachetools import TTLCache

from ..config import settings

logger = logging.getLogger(__name__)


class ESIClient:
    """
    Client for interacting with the EVE Online ESI API.
    
    Handles rate limiting, caching, and error handling for ESI requests.
    """
    
    def __init__(self):
        self.base_url = settings.ESI_BASE_URL
        self.user_agent = settings.ESI_USER_AGENT
        self.client_id = settings.ESI_CLIENT_ID
        self.client_secret = settings.ESI_CLIENT_SECRET
        
        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": self.user_agent}
        )
        
        # Initialize Redis for caching
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL)
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory cache.")
            self.redis_client = None
        
        # In-memory cache as fallback
        self.memory_cache = TTLCache(maxsize=1000, ttl=settings.CACHE_TTL_SECONDS)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Don't close the client here since we're using a global instance
        # The client will be closed when the application shuts down
        pass
    
    async def close(self):
        """Explicitly close the HTTP client."""
        await self.http_client.aclose()
    
    def _get_cache_key(self, endpoint: str, params: Dict = None) -> str:
        """Generate cache key for endpoint and parameters."""
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            return f"esi:{endpoint}:{param_str}"
        return f"esi:{endpoint}"
    
    def _get_cached_data(self, cache_key: str) -> Optional[Dict]:
        """Get data from cache (Redis or memory)."""
        try:
            if self.redis_client:
                cached = self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            else:
                return self.memory_cache.get(cache_key)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None
    
    def _set_cached_data(self, cache_key: str, data: Dict, ttl: int = None) -> None:
        """Set data in cache (Redis or memory)."""
        try:
            ttl = ttl or settings.CACHE_TTL_SECONDS
            if self.redis_client:
                self.redis_client.setex(cache_key, ttl, json.dumps(data))
            else:
                self.memory_cache[cache_key] = data
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    async def _make_request(
        self,
        endpoint: str,
        params: Dict = None,
        cache_ttl: int = None
    ) -> Optional[Dict]:
        """
        Make a request to the ESI API with caching and error handling.
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            cache_ttl: Cache TTL in seconds
            
        Returns:
            API response data or None if error
        """
        cache_key = self._get_cache_key(endpoint, params)
        
        # Check cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            logger.debug(f"Cache hit for {endpoint}")
            return cached_data
        
        # Make API request
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            logger.debug(f"Making ESI request to {url}")
            response = await self.http_client.get(url, params=params or {})
            
            if response.status_code == 200:
                data = response.json()
                
                # Cache the response
                self._set_cached_data(cache_key, data, cache_ttl)
                
                logger.debug(f"ESI request successful: {url}")
                return data
            
            elif response.status_code == 404:
                logger.warning(f"ESI endpoint not found: {url}")
                return None
            
            elif response.status_code == 420:  # Error limited
                logger.warning("ESI rate limit hit, backing off")
                await asyncio.sleep(60)  # Wait 1 minute
                return None
            
            else:
                logger.error(f"ESI request failed: {response.status_code} - {response.text}")
                return None
                
        except httpx.TimeoutException:
            logger.error(f"ESI request timeout: {url}")
            return None
        except Exception as e:
            logger.error(f"ESI request error: {e}")
            return None
    
    async def get_faction_warfare_systems(self) -> Optional[List[Dict]]:
        """
        Get faction warfare system data.
        
        Returns:
            List of system data with control information
        """
        return await self._make_request(
            "fw/systems/",
            cache_ttl=settings.SYSTEM_CACHE_TTL_SECONDS
        )
    
    async def get_faction_warfare_stats(self) -> Optional[Dict]:
        """
        Get faction warfare statistics.
        
        Returns:
            Faction warfare statistics
        """
        return await self._make_request(
            "fw/stats/",
            cache_ttl=settings.CACHE_TTL_SECONDS
        )
    
    async def get_faction_warfare_leaderboards(self) -> Optional[Dict]:
        """
        Get faction warfare leaderboards.
        
        Returns:
            Faction warfare leaderboards data
        """
        return await self._make_request(
            "fw/leaderboards/",
            cache_ttl=settings.CACHE_TTL_SECONDS
        )
    
    async def get_system_info(self, system_id: int) -> Optional[Dict]:
        """
        Get information about a specific system.
        
        Args:
            system_id: EVE system ID
            
        Returns:
            System information
        """
        return await self._make_request(
            f"universe/systems/{system_id}/",
            cache_ttl=3600  # Cache system info for 1 hour
        )
    
    async def get_corporation_info(self, corporation_id: int) -> Optional[Dict]:
        """
        Get information about a corporation.
        
        Args:
            corporation_id: EVE corporation ID
            
        Returns:
            Corporation information
        """
        return await self._make_request(
            f"corporations/{corporation_id}/",
            cache_ttl=3600  # Cache corp info for 1 hour
        )
    
    async def get_alliance_info(self, alliance_id: int) -> Optional[Dict]:
        """
        Get information about an alliance.
        
        Args:
            alliance_id: EVE alliance ID
            
        Returns:
            Alliance information
        """
        return await self._make_request(
            f"alliances/{alliance_id}/",
            cache_ttl=3600  # Cache alliance info for 1 hour
        )
    
    async def get_warzone_data(self) -> Optional[List[Dict]]:
        """
        Get warzone data from EVE Online's warzone API (not ESI).
        This includes advantage data that's not available in ESI.
        
        Returns:
            List of warzone system data with advantage information
        """
        try:
            # Use the EVE Online warzone API directly
            warzone_url = "https://www.eveonline.com/api/warzone/"
            
            response = await self.http_client.get(warzone_url)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Fetched warzone data for {len(data)} systems")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch warzone data: {e}")
            return None
    
    async def get_killmails_for_system(
        self,
        system_id: int,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Optional[List[Dict]]:
        """
        Get killmails for a specific system within a date range.
        
        Note: This is a simplified implementation. In practice, you'd need
        to use zkillboard API or other sources for historical killmail data.
        
        Args:
            system_id: EVE system ID
            start_date: Start date for killmails
            end_date: End date for killmails
            
        Returns:
            List of killmail data
        """
        # This would typically require additional API calls or third-party services
        # For now, return empty list as placeholder
        logger.info(f"Killmail fetching for system {system_id} not yet implemented")
        return []
    
    async def get_killmail_details(self, killmail_id: int, killmail_hash: str) -> Optional[Dict]:
        """
        Get full killmail details from ESI API.
        
        Args:
            killmail_id: Killmail ID
            killmail_hash: Killmail hash
            
        Returns:
            Full killmail data with victim/attacker details
        """
        return await self._make_request(
            f"killmails/{killmail_id}/{killmail_hash}/",
            cache_ttl=3600  # Cache killmail details for 1 hour
        )

    async def get_faction_info(self, faction_id: int) -> Optional[Dict]:
        """
        Get information about a faction.
        
        Args:
            faction_id: EVE faction ID
            
        Returns:
            Faction information
        """
        return await self._make_request(
            f"universe/factions/",
            cache_ttl=86400  # Cache faction info for 24 hours
        )


# Global ESI client instance
esi_client = ESIClient()
