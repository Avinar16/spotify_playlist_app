# app/infrastructure/lastfm_client.py
import asyncio

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
        async with httpx.AsyncClient() as client:
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
            logger.warning(f"Failed to get similar artists for {artist_name}: {e}")
            return []

    async def get_top_tracks(self, artist_name: str, limit: int = 5) -> list[dict]:
        try:
            data = await self._request("artist.gettoptracks", {
                "artist": artist_name,
                "limit": limit
            })
            tracks = data.get("toptracks", {}).get("track", [])
            return [{"title": t["name"], "artist": t["artist"]["name"]} for t in tracks]
        except Exception as e:
            logger.warning(f"Failed to get top tracks for {artist_name}: {e}")
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
