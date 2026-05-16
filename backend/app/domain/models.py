from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class User:
    """Domain User model"""
    id: str
    email: str
    username: str
    created_at: datetime
    updated_at: Optional[datetime] = None


@dataclass
class Playlist:
    """Domain Playlist model"""
    id: str
    name: str
    description: Optional[str]
    owner_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None


@dataclass
class PlaylistTrack:
    """Domain PlaylistTrack model"""
    id: str
    playlist_id: str
    spotify_track_id: str
    added_by_id: str
    added_at: datetime
