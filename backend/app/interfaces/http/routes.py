from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database.database import get_db
from app.infrastructure.database.models import UserModel, PlaylistModel
from app.interfaces.schemas import (
    HealthResponse,
    PlaylistCreate,
    PlaylistResponse,
    PlaylistTrackResponse,
    UserResponse,
)
from app.interfaces.http.auth_routes import get_current_user_id
import uuid

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint with DB connectivity test"""
    try:
        # Test DB connection
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
    """List playlists for current user (owned or collaborated)"""
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
    """Create a new playlist"""
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


@router.get("/api/playlists/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific playlist"""
    result = await db.execute(
        select(PlaylistModel).where(PlaylistModel.id == playlist_id)
    )
    playlist = result.scalar_one_or_none()
    
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )
    
    return playlist


@router.get("/api/playlists/{playlist_id}/tracks", response_model=list[PlaylistTrackResponse])
async def get_playlist_tracks(
    playlist_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get tracks for a playlist"""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(PlaylistModel)
        .where(PlaylistModel.id == playlist_id)
        .options(selectinload(PlaylistModel.tracks))
    )
    playlist = result.unique().scalar_one_or_none()
    
    if not playlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playlist not found"
        )
    
    return playlist.tracks or []


@router.get("/api/test-data")
async def test_data():
    """Test endpoint to verify API is responding"""
    return {
        "message": "API is working!",
        "status": "success",
        "data": {
            "app_name": "Spotify Playlist Generator",
            "version": "0.1.0"
        }
    }
