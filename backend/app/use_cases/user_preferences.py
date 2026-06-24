import logging
import json
import asyncio
import httpx
from typing import List, Dict, Any
from collections import Counter
from app.core.exceptions import AuthenticationError, ValidationError
from app.infrastructure.spotify.token_utils import refresh_spotify_token

logger = logging.getLogger(__name__)


class CaptureUserTopArtistsUseCase:

    def __init__(self, spotify_client, user_repository):
        self.spotify_client = spotify_client
        self.user_repository = user_repository

    async def execute(self, user_id: str, limit: int = 30) -> Dict[str, Any]:
        try:
            user = await self.user_repository.get_by_id(user_id)
            if not user or not user.access_token:
                raise AuthenticationError("Spotify account not linked")

            token = user.access_token
            try:
                top_artists_response = await self.spotify_client.get_top_artists(
                    access_token=token,
                    limit=limit,
                    time_range="medium_term",
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code != 401:
                    raise
                token = await refresh_spotify_token(user, self.spotify_client, self.user_repository)
                top_artists_response = await self.spotify_client.get_top_artists(
                    access_token=token,
                    limit=limit,
                    time_range="medium_term",
                )

            items = top_artists_response.get("items", [])
            artist_names = [artist["name"] for artist in items]

            await self.user_repository.update_top_artists(user_id, json.dumps(artist_names))
            logger.info(f"Captured {len(artist_names)} top artists for user {user_id}")

            return {
                "artists": artist_names,
                "count": len(artist_names)
            }

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error capturing top artists: {str(e)}")
            raise ValidationError(f"Failed to capture top artists: {str(e)}")


class GetUserFavoriteGenresUseCase:

    def __init__(self, spotify_client, user_repository, lastfm_client):
        self.spotify_client = spotify_client
        self.user_repository = user_repository
        self.lastfm_client = lastfm_client

    async def execute(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        Fetches top artists, saves them, then derives genres via Last.fm.
        Also updates user.top_artists as a side effect.
        """
        try:
            user = await self.user_repository.get_by_id(user_id)
            if not user or not user.access_token:
                raise AuthenticationError("Spotify account not linked")

            token = user.access_token
            try:
                top_artists = await self.spotify_client.get_top_artists(
                    access_token=token,
                    limit=limit,
                    time_range="medium_term",
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code != 401:
                    raise
                token = await refresh_spotify_token(user, self.spotify_client, self.user_repository)
                top_artists = await self.spotify_client.get_top_artists(
                    access_token=token,
                    limit=limit,
                    time_range="medium_term",
                )

            items = top_artists.get("items", [])
            artist_names = [x["name"] for x in items]

            await self.user_repository.update_top_artists(user_id, json.dumps(artist_names))

            all_genres = await self.lastfm_client.get_top_genres(artist_names)

            if all_genres:
                genre_counts = Counter(all_genres)
                top_genres = [genre for genre, _ in genre_counts.most_common(20)]
            else:
                top_genres = []

            user.favorite_genres = json.dumps(top_genres)
            await self.user_repository.update_favorite_genres(user_id, user.favorite_genres)

            logger.info(f"Updated favorite genres for user {user_id}: {top_genres}")

            return {
                "genres": top_genres,
                "count": len(top_genres)
            }

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error fetching favorite genres: {str(e)}")
            raise ValidationError(f"Failed to fetch favorite genres: {str(e)}")


class GetUserGenresUseCase:

    def __init__(self, user_repository):
        self.user_repository = user_repository

    async def execute(self, user_id: str) -> Dict[str, Any]:
        try:
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise ValidationError("User not found")

            genres = []
            if user.favorite_genres:
                genres = json.loads(user.favorite_genres)

            return {
                "genres": genres,
                "count": len(genres)
            }
        except Exception as e:
            logger.error(f"Error getting user genres: {str(e)}")
            raise ValidationError(f"Failed to get genres: {str(e)}")
