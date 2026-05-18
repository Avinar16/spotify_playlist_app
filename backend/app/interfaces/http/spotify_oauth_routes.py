"""Spotify OAuth routes"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.database import get_db
from app.infrastructure.database.user_repository import UserRepository
from app.infrastructure.spotify.client import SpotifyClient
from app.use_cases.spotify_auth import (
    GenerateSpotifyAuthUrlUseCase,
    LinkSpotifyAccountUseCase,
    UnlinkSpotifyAccountUseCase,
)
from app.use_cases.user_preferences import CaptureUserTopArtistsUseCase
from app.core.exceptions import AuthenticationError, ValidationError
from app.interfaces.http.auth_routes import get_current_user_id
from app.config import settings
from pydantic import BaseModel

router = APIRouter(prefix="/api/spotify", tags=["spotify"])
logger = logging.getLogger(__name__)


class SpotifyAuthUrlResponse(BaseModel):
    auth_url: str
    code_verifier: str


class SpotifyCallbackRequest(BaseModel):
    code: str
    code_verifier: str


class SpotifyAccountResponse(BaseModel):
    spotify_id: str
    email: str
    display_name: str


@router.get("/auth-url", response_model=SpotifyAuthUrlResponse)
async def get_spotify_auth_url(
    user_id: str = Depends(get_current_user_id),
):
    """Get Spotify authorization URL with PKCE"""
    try:
        use_case = GenerateSpotifyAuthUrlUseCase(settings)
        result = use_case.execute()
        return SpotifyAuthUrlResponse(**result)
    except Exception as e:
        logger.error(f"Error generating Spotify auth URL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Spotify auth URL"
        )


@router.get("/callback")
async def spotify_callback(code: str = None, error: str = None, state: str = None):
    """Spotify OAuth callback - redirects back to frontend callback page"""
    if error:
        # Redirect to frontend callback with error
        return HTMLResponse(f"""
        <html>
            <head><title>Spotify Auth</title></head>
            <body>
                <script>
                    window.opener.postMessage({{
                        type: 'SPOTIFY_AUTH_ERROR',
                        error: '{error}'
                    }}, '*');
                    window.close();
                </script>
            </body>
        </html>
        """)
    
    if code:
        # Redirect to frontend callback with code
        return HTMLResponse(f"""
        <html>
            <head><title>Spotify Auth</title></head>
            <body>
                <script>
                    window.opener.postMessage({{
                        type: 'SPOTIFY_AUTH_CODE',
                        code: '{code}'
                    }}, '*');
                    window.close();
                </script>
            </body>
        </html>
        """)
    
    return {
        "error": "No authorization code or error received"
    }


@router.post("/link", response_model=SpotifyAccountResponse)
async def link_spotify_account(
    request: SpotifyCallbackRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Link Spotify account to user profile"""
    try:
        user_repository = UserRepository(db)
        spotify_client = SpotifyClient()
        use_case = LinkSpotifyAccountUseCase(user_repository, spotify_client)
        
        result = await use_case.execute(
            user_id=user_id,
            code=request.code,
            code_verifier=request.code_verifier,
        )
        
        # Capture top artists after successful link
        capture_artists = CaptureUserTopArtistsUseCase(spotify_client, user_repository)
        await capture_artists.execute(user_id)
        
        # Ensure commit
        await db.commit()
        
        return SpotifyAccountResponse(**result)
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error linking Spotify account: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to link Spotify account"
        )


@router.post("/unlink")
async def unlink_spotify_account(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Unlink Spotify account from user profile"""
    try:
        user_repository = UserRepository(db)
        use_case = UnlinkSpotifyAccountUseCase(user_repository)
        
        result = await use_case.execute(user_id=user_id)
        return result
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error unlinking Spotify account: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlink Spotify account"
        )
