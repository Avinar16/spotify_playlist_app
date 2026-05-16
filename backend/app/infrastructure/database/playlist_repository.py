"""Playlist repository for database operations"""
import logging
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.infrastructure.database.models import PlaylistModel, PlaylistTrackModel, UserModel
from uuid import uuid4

logger = logging.getLogger(__name__)


class PlaylistRepository:
    """Repository for playlist operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, playlist_id: str) -> Optional[PlaylistModel]:
        """Get playlist by ID with tracks and collaborators"""
        stmt = (
            select(PlaylistModel)
            .where(PlaylistModel.id == playlist_id)
            .options(
                selectinload(PlaylistModel.tracks),
                selectinload(PlaylistModel.collaborators)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_user_id(self, user_id: str) -> List[PlaylistModel]:
        """Get all playlists for a user (both owned and collaborated)"""
        from sqlalchemy import or_, join
        from app.infrastructure.database.models import playlist_collaborators
        
        # Query for playlists where user is owner OR collaborator
        stmt = (
            select(PlaylistModel)
            .where(
                or_(
                    PlaylistModel.owner_id == user_id,
                    PlaylistModel.id.in_(
                        select(playlist_collaborators.c.playlist_id).where(
                            playlist_collaborators.c.user_id == user_id
                        )
                    )
                )
            )
            .options(selectinload(PlaylistModel.tracks))
            .distinct()
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def create(self, playlist_id: str, name: str, description: str, owner_id: str) -> PlaylistModel:
        """Create new playlist"""
        playlist = PlaylistModel(
            id=playlist_id,
            name=name,
            description=description,
            owner_id=owner_id,
            snapshot_id=str(uuid4())
        )
        self.db.add(playlist)
        await self.db.commit()
        await self.db.refresh(playlist)
        return playlist
    
    async def update_spotify_id(self, playlist_id: str, spotify_id: str) -> Optional[PlaylistModel]:
        """Update playlist with Spotify ID"""
        playlist = await self.get_by_id(playlist_id)
        if playlist:
            playlist.spotify_id = spotify_id
            await self.db.commit()
            await self.db.refresh(playlist)
        return playlist
    
    async def add_track(
        self, 
        playlist_id: str, 
        spotify_track_id: str, 
        added_by_id: str,
        track_name: str = None,
        track_artist: str = None,
        track_image_url: str = None
    ) -> PlaylistTrackModel:
        """Add track to playlist"""
        track = PlaylistTrackModel(
            id=str(uuid4()),
            playlist_id=playlist_id,
            spotify_track_id=spotify_track_id,
            added_by_id=added_by_id,
            track_name=track_name,
            track_artist=track_artist,
            track_image_url=track_image_url
        )
        self.db.add(track)
        await self.db.commit()
        await self.db.refresh(track)
        return track
    
    async def remove_track(self, track_id: str) -> bool:
        """Remove track from playlist"""
        stmt = select(PlaylistTrackModel).where(PlaylistTrackModel.id == track_id)
        result = await self.db.execute(stmt)
        track = result.scalar_one_or_none()
        
        if track:
            await self.db.delete(track)
            await self.db.commit()
            return True
        return False
    
    async def get_tracks(self, playlist_id: str) -> List[PlaylistTrackModel]:
        """Get all tracks in playlist"""
        stmt = select(PlaylistTrackModel).where(PlaylistTrackModel.playlist_id == playlist_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def add_collaborator(self, playlist_id: str, user_id: str) -> bool:
        """Add collaborator to playlist"""
        # Fetch playlist with eager-loaded collaborators
        stmt = (
            select(PlaylistModel)
            .where(PlaylistModel.id == playlist_id)
            .options(selectinload(PlaylistModel.collaborators))
        )
        result = await self.db.execute(stmt)
        playlist = result.scalar_one_or_none()
        
        if not playlist:
            return False
        
        user = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user_obj = user.scalar_one_or_none()
        if not user_obj:
            return False
        
        if user_obj not in playlist.collaborators:
            playlist.collaborators.append(user_obj)
            await self.db.commit()
            await self.db.refresh(playlist)
        
        return True
    
    async def remove_collaborator(self, playlist_id: str, user_id: str) -> bool:
        """Remove collaborator from playlist"""
        # Fetch playlist with eager-loaded collaborators
        stmt = (
            select(PlaylistModel)
            .where(PlaylistModel.id == playlist_id)
            .options(selectinload(PlaylistModel.collaborators))
        )
        result = await self.db.execute(stmt)
        playlist = result.scalar_one_or_none()
        
        if not playlist:
            return False
        
        user = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user_obj = user.scalar_one_or_none()
        if not user_obj:
            return False
        
        if user_obj in playlist.collaborators:
            playlist.collaborators.remove(user_obj)
            await self.db.commit()
            await self.db.refresh(playlist)
        
        return True
    
    async def get_collaborators(self, playlist_id: str) -> List[UserModel]:
        """Get all collaborators for playlist"""
        stmt = (
            select(PlaylistModel)
            .where(PlaylistModel.id == playlist_id)
            .options(selectinload(PlaylistModel.collaborators))
        )
        result = await self.db.execute(stmt)
        playlist = result.scalar_one_or_none()
        return playlist.collaborators if playlist else []
