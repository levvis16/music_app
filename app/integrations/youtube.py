import json
import logging
from typing import List, Optional
from urllib.parse import quote_plus

import aiohttp
from redis.asyncio import Redis

from app.core.config import settings
from app.database.schemas import SongSearchResult, SongProvider
from app.redis_client import get_redis

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CACHE_TTL = 3600  # 1 hour


class YouTubeClient:
    def __init__(self, api_key: Optional[str] = None, redis: Optional[Redis] = None):
        self.api_key = api_key or settings.youtube_api_key
        self._redis = redis
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _get_redis(self) -> Optional[Redis]:
        if self._redis is None:
            try:
                self._redis = await get_redis()
            except Exception as e:
                logger.warning(f"Failed to get Redis connection: {e}")
                self._redis = None
        return self._redis

    def _build_cache_key(self, query: str, limit: int) -> str:
        return f"search:youtube:{quote_plus(query)}:{limit}"

    async def _get_cached(self, cache_key: str) -> Optional[List[SongSearchResult]]:
        redis = await self._get_redis()
        if not redis:
            return None
        try:
            cached = await redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return [SongSearchResult(**item) for item in data]
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None

    async def _set_cache(self, cache_key: str, results: List[SongSearchResult]) -> None:
        redis = await self._get_redis()
        if not redis:
            return
        try:
            data = [item.model_dump() for item in results]
            await redis.setex(cache_key, CACHE_TTL, json.dumps(data))
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    async def search(
        self,
        query: str,
        limit: int = 10,
        use_cache: bool = True
    ) -> List[SongSearchResult]:
        """
        Search YouTube for music tracks.
        
        Args:
            query: Search query string
            limit: Maximum number of results (1-20)
            use_cache: Whether to use Redis cache
            
        Returns:
            List of SongSearchResult objects
        """
        if not self.api_key:
            logger.error("YouTube API key not configured")
            return []

        limit = max(1, min(limit, 20))
        cache_key = self._build_cache_key(query, limit)

        # Try cache first
        if use_cache:
            cached = await self._get_cached(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for query: {query}")
                return cached

        try:
            # Step 1: Search for videos
            video_ids = await self._search_video_ids(query, limit)
            if not video_ids:
                return []

            # Step 2: Get video details (duration, etc.)
            results = await self._get_video_details(video_ids)

            # Cache results
            if use_cache and results:
                await self._set_cache(cache_key, results)

            return results

        except aiohttp.ClientError as e:
            logger.error(f"YouTube API request failed: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error in YouTube search: {e}")
            return []

    async def _search_video_ids(self, query: str, limit: int) -> List[str]:
        """Search for video IDs using YouTube Data API v3."""
        session = await self._get_session()
        
        params = {
            "part": "snippet",
            "type": "video",
            "videoCategoryId": "10",  # Music category
            "maxResults": limit,
            "q": query,
            "key": self.api_key,
        }

        async with session.get(YOUTUBE_SEARCH_URL, params=params) as response:
            if response.status == 403:
                logger.error("YouTube API key invalid or quota exceeded")
                return []
            if response.status != 200:
                logger.error(f"YouTube search API error: {response.status}")
                return []

            data = await response.json()
            items = data.get("items", [])
            return [item["id"]["videoId"] for item in items if item.get("id", {}).get("videoId")]

    async def _get_video_details(self, video_ids: List[str]) -> List[SongSearchResult]:
        """Get video details (duration, thumbnails) for a list of video IDs."""
        if not video_ids:
            return []

        session = await self._get_session()
        
        params = {
            "part": "contentDetails,snippet",
            "id": ",".join(video_ids),
            "key": self.api_key,
        }

        async with session.get(YOUTUBE_VIDEOS_URL, params=params) as response:
            if response.status != 200:
                logger.error(f"YouTube videos API error: {response.status}")
                return []

            data = await response.json()
            items = data.get("items", [])

            results = []
            for item in items:
                try:
                    video_id = item["id"]
                    snippet = item.get("snippet", {})
                    content_details = item.get("contentDetails", {})

                    # Parse duration (ISO 8601 format: PT4M13S)
                    duration = self._parse_duration(content_details.get("duration", ""))

                    # Get best thumbnail
                    thumbnails = snippet.get("thumbnails", {})
                    thumbnail = (
                        thumbnails.get("high", {}).get("url")
                        or thumbnails.get("medium", {}).get("url")
                        or thumbnails.get("default", {}).get("url")
                    )

                    # Extract artist from title if possible
                    title = snippet.get("title", "")
                    artist = snippet.get("channelTitle", "")
                    
                    # Try to split "Artist - Title" format
                    if " - " in title and not artist:
                        parts = title.split(" - ", 1)
                        artist, title = parts[0], parts[1]

                    results.append(SongSearchResult(
                        external_id=video_id,
                        title=title,
                        artist=artist if artist else None,
                        duration=duration,
                        thumbnail=thumbnail,
                        provider=SongProvider.YOUTUBE
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse video item: {e}")
                    continue

            return results

    @staticmethod
    def _parse_duration(duration_str: str) -> Optional[int]:
        """Parse ISO 8601 duration (PT4M13S) to seconds."""
        if not duration_str or not duration_str.startswith("PT"):
            return None
        
        try:
            # Simple parser for PT#H#M#S format
            duration_str = duration_str[2:]  # Remove "PT"
            hours = 0
            minutes = 0
            seconds = 0
            
            if "H" in duration_str:
                hours, duration_str = duration_str.split("H")
                hours = int(hours)
            if "M" in duration_str:
                minutes, duration_str = duration_str.split("M")
                minutes = int(minutes)
            if "S" in duration_str:
                seconds = int(duration_str.replace("S", ""))
            
            return hours * 3600 + minutes * 60 + seconds
        except Exception:
            return None

    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()


# Global instance
youtube_client = YouTubeClient()