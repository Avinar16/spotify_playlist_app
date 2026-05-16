"""Spotify authentication use cases"""
import secrets
from app.core.exceptions import AuthenticationError, ValidationError


class GenerateSpotifyAuthUrlUseCase:
    """Generate Spotify OAuth authorization URL with PKCE"""
    
    def __init__(self, settings):
        self.settings = settings
    
    def execute(self) -> dict:
        """Generate PKCE challenge and auth URL"""
        # Generate PKCE parameters
        code_verifier = secrets.token_urlsafe(128)[:128]
        import hashlib
        import base64
        from urllib.parse import quote
        
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        # Build auth URL with required scopes
        scopes = [
            "user-read-private",
            "user-read-email",
            "user-top-read",
            "playlist-modify-public",
            "playlist-modify-private",
        ]
        scope_string = quote(" ".join(scopes))
        
        auth_url = (
            "https://accounts.spotify.com/authorize?"
            f"client_id={self.settings.SPOTIFY_CLIENT_ID}&"
            "response_type=code&"
            f"redirect_uri={quote(self.settings.SPOTIFY_REDIRECT_URI)}&"
            f"scope={scope_string}&"
            f"code_challenge={code_challenge}&"
            "code_challenge_method=S256&"
            "show_dialog=true"
        )
        
        return {
            "auth_url": auth_url,
            "code_verifier": code_verifier,
        }


class LinkSpotifyAccountUseCase:
    """Exchange Spotify auth code for access token and link to user"""
    
    def __init__(self, user_repository, spotify_client):
        self.user_repository = user_repository
        self.spotify_client = spotify_client
    
    async def execute(self, user_id: str, code: str, code_verifier: str) -> dict:
        """Exchange code for tokens and link Spotify account"""
        # Exchange code for access token
        token_response = await self.spotify_client.get_access_token(code, code_verifier)
        
        if not token_response or "access_token" not in token_response:
            raise AuthenticationError("Failed to get Spotify access token")
        
        access_token = token_response["access_token"]
        refresh_token = token_response.get("refresh_token")
        
        # Get user profile from Spotify
        profile = await self.spotify_client.get_current_user(access_token)
        
        if not profile or "id" not in profile:
            raise AuthenticationError("Failed to fetch Spotify profile")
        
        spotify_id = profile["id"]
        
        # Update user with Spotify info
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValidationError("User not found")
        
        # Save tokens
        await self.user_repository.update_spotify_tokens(
            user_id=user_id,
            spotify_id=spotify_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )
        
        return {
            "spotify_id": spotify_id,
            "email": profile.get("email"),
            "display_name": profile.get("display_name"),
        }


class UnlinkSpotifyAccountUseCase:
    """Remove Spotify account link from user"""
    
    def __init__(self, user_repository):
        self.user_repository = user_repository
    
    async def execute(self, user_id: str) -> dict:
        """Unlink Spotify account"""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValidationError("User not found")
        
        await self.user_repository.clear_spotify_tokens(user_id)
        
        return {"success": True}
