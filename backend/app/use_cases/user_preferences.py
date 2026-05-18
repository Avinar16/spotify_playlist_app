"""User preferences use cases (genres, taste profile)"""
import logging
import json
from typing import List, Dict, Any
from collections import Counter
from app.core.exceptions import AuthenticationError, ValidationError

logger = logging.getLogger(__name__)


class GetUserFavoriteGenresUseCase:
    """Get user's favorite genres from their top tracks"""

    def __init__(self, spotify_client, user_repository, lastfm_client):
        self.spotify_client = spotify_client
        self.user_repository = user_repository
        self.lastfm_client = lastfm_client

    async def execute(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        Fetch user's favorite genres from their top artists.
        Saves them to user record for future use.
        """
        try:
            # Get user and their Spotify token
            user = await self.user_repository.get_by_id(user_id)
            if not user or not user.access_token:
                raise AuthenticationError("Spotify account not linked")

            # Fetch user's top artists (which already contain genres)
            top_artists = await self.spotify_client.get_top_artists(
                access_token=user.access_token,
                limit=limit,
                time_range="medium_term"
            )

            artists = top_artists.get("items", [])
            # logger.info(artists)
            #logger.info(f"Fetched {len(artists)} top artists for user")
            all_genres = await self.lastfm_client.get_top_genres([x["name"] for x in artists])
            #logger.info(f"Total genres collected: {len(all_genres)}")

            # Count genre occurrences and get top 10
            if all_genres:
                genre_counts = Counter(all_genres)
                top_genres = [genre for genre, _ in genre_counts.most_common(20)]
            else:
                top_genres = []

            # Save to user record
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
    """Get user's previously saved favorite genres"""

    def __init__(self, user_repository):
        self.user_repository = user_repository

    async def execute(self, user_id: str) -> Dict[str, Any]:
        """Get user's saved favorite genres"""
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
