from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database.database import get_db
from app.infrastructure.database.models import UserModel, PlaylistModel
from app.interfaces.schemas import (
    HealthResponse,
    PlaylistCreate,
    PlaylistResponse,
    UserResponse,
)
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
async def list_playlists(db: AsyncSession = Depends(get_db)):
    """List all playlists (MVP - no auth)"""
    result = await db.execute(select(PlaylistModel))
    playlists = result.scalars().all()
    return playlists


@router.post("/api/playlists", response_model=PlaylistResponse)
async def create_playlist(
    playlist: PlaylistCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new playlist (MVP - no auth, hardcoded owner)"""
    new_playlist = PlaylistModel(
        id=str(uuid.uuid4()),
        name=playlist.name,
        description=playlist.description,
        owner_id="test-user-1",  # MVP hardcoded
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
