import base64
import hashlib
import secrets
from typing import Optional
import httpx
from app.config import settings


class SpotifyClient:
    """Spotify API client with OAuth2 PKCE flow support"""
    
    BASE_URL = "https://api.spotify.com/v1"
    AUTH_URL = "https://accounts.spotify.com/authorize"
    TOKEN_URL = "https://accounts.spotify.com/api/token"
    
    def __init__(self):
        self.client_id = settings.SPOTIFY_CLIENT_ID
        self.client_secret = settings.SPOTIFY_CLIENT_SECRET
        self.redirect_uri = settings.SPOTIFY_REDIRECT_URI
    
    @staticmethod
    def generate_pkce_pair() -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("utf-8")).digest()
        ).decode("utf-8").rstrip("=")
        return code_verifier, code_challenge
    
    def get_auth_url(self, state: str, code_challenge: str, scopes: Optional[list[str]] = None) -> str:
        """Generate Spotify authorization URL"""
        if scopes is None:
            scopes = [
                "user-read-private",
                "user-read-email",
                "user-top-read",
                "playlist-modify-public",
                "playlist-modify-private",
            ]
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": " ".join(scopes),
            "code_challenge_method": "S256",
            "code_challenge": code_challenge,
        }
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.AUTH_URL}?{query_string}"
    
    async def get_access_token(self, code: str, code_verifier: str) -> dict:
        """Exchange authorization code for access token using PKCE"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "client_id": self.client_id,
                    "code_verifier": code_verifier,
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Refresh access token using refresh token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def get_current_user(self, access_token: str) -> dict:
        """Get current user profile"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
    
    async def get_top_tracks(self, access_token: str, limit: int = 20, offset: int = 0, time_range: str = "medium_term") -> dict:
        """Get user's top tracks"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/me/top/tracks",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "limit": limit,
                    "offset": offset,
                    "time_range": time_range,
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def get_audio_features(self, access_token: str, track_ids: list[str]) -> dict:
        """Get audio features for tracks"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/audio-features",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"ids": ",".join(track_ids)},
            )
            response.raise_for_status()
            return response.json()
    
    async def get_recommendations(self, access_token: str, seed_tracks: list[str], limit: int = 20) -> dict:
        """Get recommendations based on seed tracks"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/recommendations",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "seed_tracks": ",".join(seed_tracks[:5]),
                    "limit": limit,
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def search_tracks(self, access_token: str, query: str, limit: int = 20) -> list[dict]:
        """Search for tracks"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/search",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "q": query,
                    "type": "track",
                    "limit": limit,
                },
            )
            response.raise_for_status()
            data = response.json()
            # Return simplified track data
            return [
                {
                    "id": track["id"],
                    "name": track["name"],
                    "artist": ", ".join([a["name"] for a in track.get("artists", [])]),
                    "album": track.get("album", {}).get("name", ""),
                    "image": track.get("album", {}).get("images", [{}])[0].get("url"),
                    "duration_ms": track.get("duration_ms", 0),
                    "preview_url": track.get("preview_url"),
                }
                for track in data.get("tracks", {}).get("items", [])
            ]
    
    async def get_track(self, access_token: str, track_id: str) -> dict:
        """Get track details by ID"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/tracks/{track_id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            track = response.json()
            return {
                "id": track["id"],
                "name": track["name"],
                "artist": ", ".join([a["name"] for a in track.get("artists", [])]),
                "album": track.get("album", {}).get("name", ""),
                "image": track.get("album", {}).get("images", [{}])[0].get("url"),
                "duration_ms": track.get("duration_ms", 0),
                "preview_url": track.get("preview_url"),
            }
    
    async def create_playlist(self, access_token: str, name: str, description: str = "") -> dict:
        """Create a playlist for current user"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/me/playlists",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "name": name,
                    "description": description,
                    "public": False,
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def add_tracks_to_playlist(self, access_token: str, playlist_id: str, track_ids: list[str]) -> dict:
        """Add tracks to a playlist"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/playlists/{playlist_id}/items",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"uris": [f"spotify:track:{track_id}" for track_id in track_ids]},
            )
            response.raise_for_status()
            return response.json()
