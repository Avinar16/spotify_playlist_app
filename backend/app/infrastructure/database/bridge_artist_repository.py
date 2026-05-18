"""Bridge artist repository for caching playlist bridge artists"""
import logging
from uuid import uuid4
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models import PlaylistBridgeArtistModel

logger = logging.getLogger(__name__)


class BridgeArtistRepository:
    """Repository for managing cached bridge artists"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_bridge_artists(
        self,
        playlist_id: str,
        artists: list[tuple[str, float]]
    ) -> None:
        """
        Save bridge artists for a playlist, replacing any existing ones.
        
        Args:
            playlist_id: Playlist ID
            artists: List of (artist_name, score) tuples
        """
        # Delete existing bridge artists for this playlist
        await self.session.execute(
            delete(PlaylistBridgeArtistModel).where(
                PlaylistBridgeArtistModel.playlist_id == playlist_id
            )
        )

        # Insert new bridge artists
        for artist_name, score in artists:
            model = PlaylistBridgeArtistModel(
                id=str(uuid4()),
                playlist_id=playlist_id,
                artist_name=artist_name,
                score=score
            )
            self.session.add(model)

        await self.session.commit()
        logger.info(f"Saved {len(artists)} bridge artists for playlist {playlist_id}")

    async def get_bridge_artists(self, playlist_id: str) -> list[tuple[str, float]]:
        """
        Get cached bridge artists for a playlist.
        
        Returns:
            List of (artist_name, score) tuples, sorted by score descending
        """
        result = await self.session.execute(
            select(PlaylistBridgeArtistModel)
            .where(PlaylistBridgeArtistModel.playlist_id == playlist_id)
            .order_by(PlaylistBridgeArtistModel.score.desc())
        )
        models = result.scalars().all()
        return [(m.artist_name, m.score) for m in models]

    async def delete_bridge_artists(self, playlist_id: str) -> None:
        """Delete all bridge artists for a playlist"""
        await self.session.execute(
            delete(PlaylistBridgeArtistModel).where(
                PlaylistBridgeArtistModel.playlist_id == playlist_id
            )
        )
        await self.session.commit()
        logger.info(f"Deleted bridge artists for playlist {playlist_id}")
