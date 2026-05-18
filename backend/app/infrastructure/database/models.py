from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Table, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Association table for playlist collaborators
playlist_collaborators = Table(
    'playlist_collaborators',
    Base.metadata,
    Column('playlist_id', String, ForeignKey('playlists.id'), primary_key=True),
    Column('user_id', String, ForeignKey('users.id'), primary_key=True),
)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # Optional for OAuth users
    spotify_id = Column(String(255), unique=True, nullable=True, index=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    favorite_genres = Column(Text, nullable=True)  # JSON array of favorite genres
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    playlists = relationship("PlaylistModel", back_populates="owner", foreign_keys="PlaylistModel.owner_id")
    collaborated_playlists = relationship(
        "PlaylistModel",
        secondary=playlist_collaborators,
        back_populates="collaborators"
    )


class PlaylistModel(Base):
    __tablename__ = "playlists"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    spotify_id = Column(String(255), nullable=True, unique=True, index=True)  # Spotify playlist ID
    snapshot_id = Column(String(255), nullable=True)  # For collaborative editing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("UserModel", back_populates="playlists", foreign_keys=[owner_id])
    collaborators = relationship(
        "UserModel",
        secondary=playlist_collaborators,
        back_populates="collaborated_playlists"
    )
    tracks = relationship("PlaylistTrackModel", back_populates="playlist", cascade="all, delete-orphan")


class PlaylistTrackModel(Base):
    __tablename__ = "playlist_tracks"

    id = Column(String(36), primary_key=True)
    playlist_id = Column(String(36), ForeignKey('playlists.id'), nullable=False, index=True)
    spotify_track_id = Column(String(255), nullable=False)
    track_name = Column(String(255), nullable=True)
    track_artist = Column(String(255), nullable=True)
    track_image_url = Column(Text, nullable=True)  # Album cover image
    track_genres = Column(Text, nullable=True)  # JSON array of genres stored as string
    added_by_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    playlist = relationship("PlaylistModel", back_populates="tracks")
    added_by = relationship("UserModel")
