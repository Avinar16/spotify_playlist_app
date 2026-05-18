"""Playlist management routes"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.database import get_db
from app.infrastructure.database.playlist_repository import PlaylistRepository
from app.infrastructure.database.user_repository import UserRepository
from app.infrastructure.database.bridge_artist_repository import BridgeArtistRepository
from app.infrastructure.spotify.client import SpotifyClient
from app.infrastructure.lastfm.client import LastFmClient
from app.use_cases.playlists import (
    SearchTracksUseCase,
    AddTrackToPlaylistUseCase,
    CreateSpotifyPlaylistUseCase,
    SyncTracksToSpotifyUseCase,
    InviteCollaboratorUseCase,
    GetPlaylistCollaboratorsUseCase,
    RemoveCollaboratorUseCase,
    GeneratePlaylistFromBridgeUseCase,
    FindBridgeArtistsUseCase,
)
from app.core.exceptions import AuthenticationError, ValidationError
from app.interfaces.http.auth_routes import get_current_user_id
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/api/playlist", tags=["playlist"])
logger = logging.getLogger(__name__)


class SearchTracksRequest(BaseModel):
    query: str
    limit: int = 20


class TrackResponse(BaseModel):
    id: str
    name: str
    artist: str
    album: str
    duration_ms: int
    preview_url: Optional[str]


class AddTrackRequest(BaseModel):
    spotify_track_id: str


class CreatePlaylistRequest(BaseModel):
    name: str
    description: str = ""


class TrackInPlaylistResponse(BaseModel):
    id: str
    spotify_track_id: str
    track_name: Optional[str] = None
    track_artist: Optional[str] = None
    track_image_url: Optional[str] = None
    track_genres: Optional[List[str]] = None
    added_at: str


class InviteCollaboratorRequest(BaseModel):
    search_query: str


class CollaboratorResponse(BaseModel):
    id: str
    username: str
    email: str


class GeneratePlaylistRequest(BaseModel):
    quantity: int = 20


class BridgeArtistResponse(BaseModel):
    artist_name: str
    score: float


class BridgeArtistsWithCollaboratorsResponse(BaseModel):
    """Response with bridge artists and collaborator info"""
    bridge_artists: List[BridgeArtistResponse]
    collaborators: List[Dict[str, Any]]  # {id, username, top_artists: [str]}


class CollaboratorWithArtistsResponse(BaseModel):
    id: str
    username: str
    top_artists: List[str]


@router.post("/{playlist_id}/generate", response_model=Dict[str, Any])
async def generate_playlist(
    playlist_id: str,
    request: GeneratePlaylistRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate and add tracks to playlist based on bridge artists"""
    try:
        playlist_repository = PlaylistRepository(db)
        user_repository = UserRepository(db)
        bridge_artist_repository = BridgeArtistRepository(db)
        spotify_client = SpotifyClient()
        lastfm_client = LastFmClient()
        use_case = GeneratePlaylistFromBridgeUseCase(spotify_client, lastfm_client, playlist_repository, user_repository)
        
        result = await use_case.execute(
            user_id=user_id,
            playlist_id=playlist_id,
            quantity=request.quantity
        )
        
        return result
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating playlist: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate playlist"
        )


@router.post("/search-tracks", response_model=List[TrackResponse])
async def search_tracks(
    request: SearchTracksRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Search for tracks on Spotify"""
    try:
        user_repository = UserRepository(db)
        spotify_client = SpotifyClient()
        use_case = SearchTracksUseCase(spotify_client, user_repository)
        
        results = await use_case.execute(
            user_id=user_id,
            query=request.query,
            limit=request.limit
        )
        
        return results
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error searching tracks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search tracks"
        )


@router.post("/{playlist_id}/add-track", response_model=TrackInPlaylistResponse)
async def add_track_to_playlist(
    playlist_id: str,
    request: AddTrackRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Add track to playlist"""
    try:
        playlist_repository = PlaylistRepository(db)
        user_repository = UserRepository(db)
        spotify_client = SpotifyClient()
        use_case = AddTrackToPlaylistUseCase(playlist_repository, user_repository, spotify_client)
        
        result = await use_case.execute(
            user_id=user_id,
            playlist_id=playlist_id,
            spotify_track_id=request.spotify_track_id
        )
        
        return result
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding track: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add track"
        )


@router.post("/{playlist_id}/create-on-spotify")
async def create_playlist_on_spotify(
    playlist_id: str,
    request: CreatePlaylistRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create playlist on Spotify and sync with local DB"""
    try:
        playlist_repository = PlaylistRepository(db)
        user_repository = UserRepository(db)
        spotify_client = SpotifyClient()
        use_case = CreateSpotifyPlaylistUseCase(spotify_client, playlist_repository, user_repository)
        
        result = await use_case.execute(
            user_id=user_id,
            playlist_id=playlist_id,
            name=request.name,
            description=request.description
        )
        
        return result
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating Spotify playlist: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create Spotify playlist"
        )


@router.post("/{playlist_id}/sync-tracks")
async def sync_tracks_to_spotify(
    playlist_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Sync all tracks in local playlist to Spotify"""
    try:
        playlist_repository = PlaylistRepository(db)
        user_repository = UserRepository(db)
        spotify_client = SpotifyClient()
        use_case = SyncTracksToSpotifyUseCase(spotify_client, playlist_repository, user_repository)
        
        result = await use_case.execute(
            user_id=user_id,
            playlist_id=playlist_id
        )
        
        return result
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error syncing tracks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync tracks"
        )


@router.get("/{playlist_id}/collaborators", response_model=List[CollaboratorResponse])
async def get_playlist_collaborators(
    playlist_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get all collaborators for a playlist"""
    try:
        playlist_repository = PlaylistRepository(db)
        user_repository = UserRepository(db)
        use_case = GetPlaylistCollaboratorsUseCase(playlist_repository, user_repository)
        
        result = await use_case.execute(
            user_id=user_id,
            playlist_id=playlist_id
        )
        
        return result
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting collaborators: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get collaborators"
        )


@router.post("/{playlist_id}/invite", response_model=CollaboratorResponse)
async def invite_collaborator(
    playlist_id: str,
    request: InviteCollaboratorRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Invite a collaborator to playlist"""
    try:
        playlist_repository = PlaylistRepository(db)
        user_repository = UserRepository(db)
        use_case = InviteCollaboratorUseCase(playlist_repository, user_repository)
        
        result = await use_case.execute(
            user_id=user_id,
            playlist_id=playlist_id,
            search_query=request.search_query
        )
        
        return result
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inviting collaborator: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to invite collaborator"
        )


@router.delete("/{playlist_id}/collaborators/{collaborator_id}")
async def remove_collaborator(
    playlist_id: str,
    collaborator_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Remove collaborator from playlist"""
    try:
        playlist_repository = PlaylistRepository(db)
        use_case = RemoveCollaboratorUseCase(playlist_repository)
        
        result = await use_case.execute(
            user_id=user_id,
            playlist_id=playlist_id,
            collaborator_id=collaborator_id
        )
        
        return result
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error removing collaborator: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove collaborator"
        )


@router.get("/{playlist_id}/bridge-artists", response_model=BridgeArtistsWithCollaboratorsResponse)
async def get_bridge_artists(
    playlist_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get cached bridge artists for a playlist along with collaborators' top artists.
    This is used by the generation popup to show both columns:
    - Column 1: Top artists from collaborators (with user labels)
    - Column 2: Bridge artists for the playlist (with scores)
    """
    try:
        playlist_repository = PlaylistRepository(db)
        user_repository = UserRepository(db)
        bridge_artist_repository = BridgeArtistRepository(db)
        lastfm_client = LastFmClient()
        
        # Get playlist and check access
        playlist = await playlist_repository.get_by_id(playlist_id)
        if not playlist:
            raise ValidationError("Playlist not found")
        
        # Check access (owner or collaborator)
        if playlist.owner_id != user_id and not any(c.id == user_id for c in playlist.collaborators):
            raise AuthenticationError("You don't have access to this playlist")
        
        # Get cached bridge artists or calculate if needed
        bridge_use_case = FindBridgeArtistsUseCase(
            lastfm_client,
            playlist_repository,
            user_repository,
            bridge_artist_repository
        )
        bridge_artists = await bridge_use_case.execute(user_id, playlist_id, limit=20)
        
        # Get collaborators with their top artists
        owner = await user_repository.get_by_id(playlist.owner_id)
        collaborators = await playlist_repository.get_collaborators(playlist_id)
        all_collaborators = [owner] + collaborators
        
        collaborators_data = []
        for collab in all_collaborators:
            import json
            top_artists = []
            if collab.top_artists:
                try:
                    top_artists = json.loads(collab.top_artists)
                except Exception:
                    pass
            
            collaborators_data.append({
                "id": collab.id,
                "username": collab.username,
                "top_artists": top_artists
            })
        
        # Format bridge artists response
        bridge_artists_response = [
            BridgeArtistResponse(artist_name=name, score=score)
            for name, score in bridge_artists
        ]
        
        return BridgeArtistsWithCollaboratorsResponse(
            bridge_artists=bridge_artists_response,
            collaborators=collaborators_data
        )
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting bridge artists: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bridge artists"
        )
