# app/infrastructure/lastfm_client.py
import asyncio
import random

import httpx
from collections import Counter
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class LastFmClient:
    BASE_URL = "https://ws.audioscrobbler.com/2.0/"

    def __init__(self):
        self.api_key = settings.LASTFM_KEY

    async def _request(self, method: str, params: dict) -> dict:
        # Increase timeout to handle slow Last.fm API responses
        timeout = httpx.Timeout(30.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(self.BASE_URL, params={
                "method": method,
                "api_key": self.api_key,
                "format": "json",
                **params
            })
            response.raise_for_status()
            return response.json()

    async def get_similar_artists(self, artist_name: str, limit: int = 10) -> list[str]:
        try:
            data = await self._request("artist.getsimilar", {
                "artist": artist_name,
                "limit": limit
            })
            artists = data.get("similarartists", {}).get("artist", [])
            return [a["name"] for a in artists]
        except Exception as e:
            logger.warning(f"Failed to get similar artists for {artist_name}: {e}", exc_info=True)
            return []

    async def get_similar_artists_with_score(self, artist_name: str, limit: int = 10) -> list[tuple[str, float]]:
        """Get similar artists with match scores (0-1)"""
        try:
            data = await self._request("artist.getsimilar", {
                "artist": artist_name,
                "limit": limit
            })
            artists = data.get("similarartists", {}).get("artist", [])
            if not isinstance(artists, list):
                artists = [artists] if artists else []
            
            result = []
            for a in artists:
                try:
                    if isinstance(a, dict) and "name" in a:
                        name = a["name"]
                        match = float(a.get("match", 0))  # match is already 0-1 from Last.fm
                        result.append((name, match))
                except Exception as item_err:
                    logger.debug(f"Skipping malformed artist item: {item_err}")
                    continue
            return result
        except Exception as e:
            logger.warning(f"Failed to get similar artists for {artist_name}: {e}", exc_info=True)
            return []

    async def get_top_tracks(self, artist_name: str, limit: int = 5) -> list[dict]:
        try:
            data = await self._request("artist.gettoptracks", {
                "artist": artist_name,
                "limit": limit
            })
            tracks = data.get("toptracks", {}).get("track", [])
            if not isinstance(tracks, list):
                tracks = [tracks] if tracks else []
            
            result = []
            for t in tracks:
                try:
                    if isinstance(t, dict) and "name" in t and "artist" in t:
                        artist_name_val = t["artist"].get("name") if isinstance(t["artist"], dict) else t["artist"]
                        result.append({"title": t["name"], "artist": artist_name_val})
                except Exception as track_err:
                    logger.debug(f"Skipping malformed track: {track_err}")
                    continue
            return result
        except Exception as e:
            logger.warning(f"Failed to get top tracks for {artist_name}: {e}", exc_info=True)
            return []

    async def get_mixed_tracks(self, artist_name: str, limit: int = 5) -> list[dict]:
        """Get 60% top tracks + 40% random tracks from pages 2-5"""
        try:
            top_count = max(1, round(limit * 0.6))
            random_count = limit - top_count
            
            # Get top tracks (page 1)
            top_data = await self._request("artist.gettoptracks", {
                "artist": artist_name,
                "limit": top_count,
                "page": 1
            })
            top_tracks = top_data.get("toptracks", {}).get("track", [])
            if not isinstance(top_tracks, list):
                top_tracks = [top_tracks] if top_tracks else []
            
            # Get random tracks from random page (2-5)
            random_page = random.randint(2, 5)
            rand_data = await self._request("artist.gettoptracks", {
                "artist": artist_name,
                "limit": random_count * 3,  # fetch with margin
                "page": random_page
            })
            rand_pool = rand_data.get("toptracks", {}).get("track", [])
            if not isinstance(rand_pool, list):
                rand_pool = [rand_pool] if rand_pool else []
            random_tracks = random.sample(rand_pool, min(random_count, len(rand_pool)))
            
            # Combine and filter valid tracks
            all_tracks = top_tracks + random_tracks
            result = []
            for t in all_tracks:
                try:
                    if isinstance(t, dict) and "name" in t and "artist" in t:
                        artist_name_val = t["artist"].get("name") if isinstance(t["artist"], dict) else t["artist"]
                        result.append({"title": t["name"], "artist": artist_name_val})
                except Exception as track_err:
                    logger.debug(f"Skipping malformed track: {track_err}")
                    continue
            return result
        except Exception as e:
            logger.warning(f"Failed to get mixed tracks for {artist_name}: {e}", exc_info=True)
            return []

    async def get_artist_tags(self, artist_name: str) -> list[str]:
        try:
            data = await self._request("artist.getinfo", {"artist": artist_name})
            tags = data.get("artist", {}).get("tags", {}).get("tag", [])
            return [t["name"].lower() for t in tags]
        except Exception as e:
            logger.warning(f"Failed to get tags for {artist_name}: {e}")
            return []

    async def get_top_genres(self, artist_names: list[str], top_n: int = 10) -> list[str]:
        """Получаем жанры для списка артистов и возвращаем топ по частоте"""
        tasks = [self.get_artist_tags(a) for a in artist_names]
        results = await asyncio.gather(*tasks)

        all_tags = []
        for tags in results:
            all_tags.extend(tags[:3])

        counter = Counter(all_tags)
        return [genre for genre, _ in counter.most_common(top_n)]
