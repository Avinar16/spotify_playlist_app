from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database.database import get_db
from app.infrastructure.database.models import UserModel, PlaylistModel
from app.infrastructure.database.playlist_repository import PlaylistRepository
from app.interfaces.schemas import (
    HealthResponse,
    PlaylistCreate,
    PlaylistResponse,
    PlaylistTrackResponse,
    UserResponse,
)
from app.interfaces.http.auth_routes import get_current_user_id
from app.use_cases.playlists import (
    GetPlaylistStateUseCase,
    DeleteTrackFromPlaylistUseCase,
    DeletePlaylistUseCase,
)
from app.core.exceptions import AuthenticationError, ValidationError
from pydantic import BaseModel
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(select(1))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="ok",
        message="Server is running",
        database=db_status
    )


@router.get("/api/playlists", response_model=list[PlaylistResponse])
async def list_playlists(
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    from app.infrastructure.database.playlist_repository import PlaylistRepository

    playlist_repository = PlaylistRepository(db)
    playlists = await playlist_repository.get_by_user_id(user_id)
    return playlists


@router.post("/api/playlists", response_model=PlaylistResponse)
async def create_playlist(
        playlist: PlaylistCreate,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    new_playlist = PlaylistModel(
        id=str(uuid.uuid4()),
        name=playlist.name,
        description=playlist.description,
        owner_id=user_id,
        snapshot_id=str(uuid.uuid4()),
    )
    db.add(new_playlist)
    await db.commit()
    await db.refresh(new_playlist)
    return new_playlist


class PlaylistUpdate(BaseModel):
    name: str
    description: Optional[str] = None


@router.patch("/api/playlists/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
        playlist_id: str,
        update: PlaylistUpdate,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    playlist_repository = PlaylistRepository(db)
    playlist = await playlist_repository.get_by_id(playlist_id)

    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")
    if playlist.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can rename the playlist")

    name = update.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Playlist name cannot be empty")

    updated = await playlist_repository.update_name(playlist_id, name, update.description)
    return updated


@router.get("/api/playlists/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
        playlist_id: str,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    playlist_repository = PlaylistRepository(db)
    playlist = await playlist_repository.get_by_id(playlist_id)

    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")

    if playlist.owner_id != user_id and not any(c.id == user_id for c in playlist.collaborators):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return playlist


@router.get("/api/playlists/{playlist_id}/tracks", response_model=list[PlaylistTrackResponse])
async def get_playlist_tracks(
        playlist_id: str,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    playlist_repository = PlaylistRepository(db)
    playlist = await playlist_repository.get_by_id(playlist_id)

    if not playlist:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playlist not found")

    if playlist.owner_id != user_id and not any(c.id == user_id for c in playlist.collaborators):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return playlist.tracks or []


@router.get("/api/test-data")
async def test_data():
    return {
        "message": "API is working!",
        "status": "success",
        "data": {
            "app_name": "Spotify Playlist Generator",
            "version": "0.1.0"
        }
    }


@router.get("/api/playlists/{playlist_id}/state")
async def get_playlist_state(
        playlist_id: str,
        last_snapshot_id: Optional[str] = None,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    """Get playlist state with snapshot_id for real-time sync"""
    try:
        playlist_repository = PlaylistRepository(db)
        use_case = GetPlaylistStateUseCase(playlist_repository)

        result = await use_case.execute(
            user_id=user_id,
            playlist_id=playlist_id,
            last_snapshot_id=last_snapshot_id
        )

        return result
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in get_playlist_state: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get playlist state"
        )


@router.delete("/api/playlists/{playlist_id}/tracks/{track_id}")
async def delete_track_from_playlist(
        playlist_id: str,
        track_id: str,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    try:
        playlist_repository = PlaylistRepository(db)
        use_case = DeleteTrackFromPlaylistUseCase(playlist_repository)

        result = await use_case.execute(
            user_id=user_id,
            playlist_id=playlist_id,
            track_id=track_id
        )

        return result
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete track"
        )


@router.delete("/api/playlists/{playlist_id}")
async def delete_playlist(
        playlist_id: str,
        user_id: str = Depends(get_current_user_id),
        db: AsyncSession = Depends(get_db)
):
    try:
        playlist_repository = PlaylistRepository(db)
        use_case = DeletePlaylistUseCase(playlist_repository)

        result = await use_case.execute(
            user_id=user_id,
            playlist_id=playlist_id
        )

        return result
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete playlist"
        )
