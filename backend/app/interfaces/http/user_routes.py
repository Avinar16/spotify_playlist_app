"""User preferences routes"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.infrastructure.database.database import get_db
from app.infrastructure.database.user_repository import UserRepository
from app.infrastructure.spotify.client import SpotifyClient
from app.use_cases.user_preferences import GetUserFavoriteGenresUseCase, GetUserGenresUseCase
from app.core.auth import verify_token
from app.core.exceptions import AuthenticationError, ValidationError
from app.interfaces.schemas import GenresResponse
from app.infrastructure.lastfm.client import LastFmClient

router = APIRouter(prefix="/api/user", tags=["user"])


async def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract user_id from Authorization header"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


@router.post("/genres/refresh", response_model=GenresResponse)
async def refresh_favorite_genres(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Fetch and save user's favorite genres from Spotify top tracks"""
    try:
        user_repo = UserRepository(db)
        spotify_client = SpotifyClient()
        lastfm_client = LastFmClient()
        use_case = GetUserFavoriteGenresUseCase(spotify_client, user_repo, lastfm_client)
        result = await use_case.execute(user_id)
        
        return GenresResponse(
            genres=result["genres"],
            count=result["count"]
        )
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/genres", response_model=GenresResponse)
async def get_favorite_genres(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get user's saved favorite genres"""
    try:
        user_repo = UserRepository(db)
        use_case = GetUserGenresUseCase(user_repo)
        result = await use_case.execute(user_id)
        
        return GenresResponse(
            genres=result["genres"],
            count=result["count"]
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
