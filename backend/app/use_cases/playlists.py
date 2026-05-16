"""Playlist management use cases"""
import logging
from typing import Optional, List, Dict, Any
from uuid import uuid4
from app.core.exceptions import ValidationError, AuthenticationError

logger = logging.getLogger(__name__)


class SearchTracksUseCase:
    """Search for tracks in Spotify"""
    
    def __init__(self, spotify_client, user_repository):
        self.spotify_client = spotify_client
        self.user_repository = user_repository
    
    async def execute(self, user_id: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for tracks by query"""
        if not query or len(query.strip()) < 2:
            raise ValidationError("Search query must be at least 2 characters")
        
        try:
            # Get user's Spotify access token
            user = await self.user_repository.get_by_id(user_id)
            if not user or not user.access_token:
                raise AuthenticationError("Spotify account not linked")
            
            results = await self.spotify_client.search_tracks(
                access_token=user.access_token,
                query=query.strip(),
                limit=limit
            )
            return results
        except AuthenticationError:
            raise
        except Exception as e:
            error_str = str(e)
            # Check if it's a 401 Unauthorized error
            if "401" in error_str or "Unauthorized" in error_str:
                raise AuthenticationError("Spotify session expired. Please reconnect your account.")
            logger.error(f"Error searching tracks: {str(e)}")
            raise ValidationError(f"Failed to search tracks: {str(e)}")


class AddTrackToPlaylistUseCase:
    """Add track to playlist"""
    
    def __init__(self, playlist_repository, user_repository, spotify_client=None):
        self.playlist_repository = playlist_repository
        self.user_repository = user_repository
        self.spotify_client = spotify_client
    
    async def execute(
        self, 
        user_id: str,
        playlist_id: str,
        spotify_track_id: str
    ) -> Dict[str, Any]:
        """Add track to playlist"""
        if not spotify_track_id or len(spotify_track_id.strip()) < 1:
            raise ValidationError("Track ID is required")
        
        # Check playlist exists and user has access
        playlist = await self.playlist_repository.get_by_id(playlist_id)
        if not playlist:
            raise ValidationError("Playlist not found")
        
        if playlist.owner_id != user_id:
            raise AuthenticationError("You don't have permission to modify this playlist")
        
        # Get track details if spotify_client is provided
        track_name = None
        track_artist = None
        track_image_url = None
        
        if self.spotify_client:
            try:
                user = await self.user_repository.get_by_id(user_id)
                if user and user.access_token:
                    track_info = await self.spotify_client.get_track(user.access_token, spotify_track_id)
                    track_name = track_info.get("name")
                    track_artist = track_info.get("artist")
                    track_image_url = track_info.get("image")
            except Exception as e:
                logger.warning(f"Could not fetch track details: {str(e)}")
        
        # Add track to playlist
        try:
            track = await self.playlist_repository.add_track(
                playlist_id=playlist_id,
                spotify_track_id=spotify_track_id,
                added_by_id=user_id,
                track_name=track_name,
                track_artist=track_artist,
                track_image_url=track_image_url
            )
            return {
                "id": track.id,
                "spotify_track_id": track.spotify_track_id,
                "track_name": track.track_name,
                "track_artist": track.track_artist,
                "track_image_url": track.track_image_url,
                "added_at": track.added_at.isoformat()
            }
        except Exception as e:
            logger.error(f"Error adding track to playlist: {str(e)}")
            raise ValidationError(f"Failed to add track: {str(e)}")


class CreateSpotifyPlaylistUseCase:
    """Create playlist in Spotify and sync to local DB"""
    
    def __init__(self, spotify_client, playlist_repository, user_repository):
        self.spotify_client = spotify_client
        self.playlist_repository = playlist_repository
        self.user_repository = user_repository
    
    async def execute(
        self,
        user_id: str,
        playlist_id: str,
        name: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """Create playlist in Spotify"""
        try:
            # Get user's Spotify access token
            user = await self.user_repository.get_by_id(user_id)
            if not user or not user.access_token:
                raise AuthenticationError("Spotify account not linked")
            
            # Create playlist in Spotify
            spotify_playlist = await self.spotify_client.create_playlist(
                access_token=user.access_token,
                name=name,
                description=description or "Created with Spotify Playlist Generator"
            )
            
            if not spotify_playlist:
                raise ValidationError("Failed to create Spotify playlist")
            
            # Update local playlist with Spotify ID
            spotify_id = spotify_playlist.get('id')
            await self.playlist_repository.update_spotify_id(playlist_id, spotify_id)
            
            return {
                "id": playlist_id,
                "spotify_id": spotify_id,
                "name": name,
                "url": spotify_playlist.get('external_urls', {}).get('spotify', '')
            }
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error creating Spotify playlist: {str(e)}")
            raise ValidationError(f"Failed to create Spotify playlist: {str(e)}")


class SyncTracksToSpotifyUseCase:
    """Sync local playlist tracks to Spotify"""
    
    def __init__(self, spotify_client, playlist_repository, user_repository):
        self.spotify_client = spotify_client
        self.playlist_repository = playlist_repository
        self.user_repository = user_repository
    
    async def execute(
        self,
        user_id: str,
        playlist_id: str
    ) -> Dict[str, Any]:
        """Sync all tracks in local playlist to Spotify"""
        try:
            # Get user's Spotify access token
            user = await self.user_repository.get_by_id(user_id)
            if not user or not user.access_token:
                raise AuthenticationError("Spotify account not linked")
            
            # Get playlist with tracks
            playlist = await self.playlist_repository.get_by_id(playlist_id)
            if not playlist:
                raise ValidationError("Playlist not found")
            
            if playlist.owner_id != user_id:
                raise AuthenticationError("You don't have permission to modify this playlist")
            
            if not playlist.spotify_id:
                raise ValidationError("Playlist is not linked to Spotify. Create it in Spotify first.")
            
            # Collect all track IDs
            track_ids = [track.spotify_track_id for track in playlist.tracks]
            
            if not track_ids:
                return {
                    "status": "success",
                    "message": "No tracks to sync",
                    "synced_count": 0
                }
            
            # Add tracks to Spotify playlist
            result = await self.spotify_client.add_tracks_to_playlist(
                access_token=user.access_token,
                playlist_id=playlist.spotify_id,
                track_ids=track_ids
            )
            
            return {
                "status": "success",
                "message": f"Synced {len(track_ids)} tracks to Spotify",
                "synced_count": len(track_ids),
                "spotify_playlist_id": playlist.spotify_id
            }
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Error syncing tracks to Spotify: {str(e)}")
            raise ValidationError(f"Failed to sync tracks: {str(e)}")


class InviteCollaboratorUseCase:
    """Invite a collaborator to playlist"""
    
    def __init__(self, playlist_repository, user_repository):
        self.playlist_repository = playlist_repository
        self.user_repository = user_repository
    
    async def execute(
        self,
        user_id: str,
        playlist_id: str,
        search_query: str
    ) -> Dict[str, Any]:
        """Invite collaborator by email or username"""
        if not search_query or len(search_query.strip()) < 1:
            raise ValidationError("Email or username is required")
        
        # Check playlist exists and user is owner
        playlist = await self.playlist_repository.get_by_id(playlist_id)
        if not playlist:
            raise ValidationError("Playlist not found")
        
        if playlist.owner_id != user_id:
            raise AuthenticationError("Only playlist owner can invite collaborators")
        
        # Search for user by email or username
        search_query = search_query.strip()
        target_user = None
        
        if "@" in search_query:
            target_user = await self.user_repository.get_by_email(search_query)
        else:
            target_user = await self.user_repository.get_by_username(search_query)
        
        if not target_user:
            raise ValidationError(f"User not found: {search_query}")
        
        if target_user.id == user_id:
            raise ValidationError("Cannot invite yourself to playlist")
        
        # Add collaborator
        success = await self.playlist_repository.add_collaborator(playlist_id, target_user.id)
        
        if not success:
            raise ValidationError("Failed to add collaborator")
        
        return {
            "id": target_user.id,
            "username": target_user.username,
            "email": target_user.email
        }


class GetPlaylistCollaboratorsUseCase:
    """Get all collaborators for a playlist"""
    
    def __init__(self, playlist_repository, user_repository):
        self.playlist_repository = playlist_repository
        self.user_repository = user_repository
    
    async def execute(self, user_id: str, playlist_id: str) -> List[Dict[str, Any]]:
        """Get collaborators for playlist"""
        # Check playlist exists and user has access
        playlist = await self.playlist_repository.get_by_id(playlist_id)
        if not playlist:
            raise ValidationError("Playlist not found")
        
        if playlist.owner_id != user_id and user_id not in [c.id for c in playlist.collaborators]:
            raise AuthenticationError("You don't have access to this playlist")
        
        collaborators = await self.playlist_repository.get_collaborators(playlist_id)
        
        return [
            {
                "id": collab.id,
                "username": collab.username,
                "email": collab.email
            }
            for collab in collaborators
        ]


class RemoveCollaboratorUseCase:
    """Remove collaborator from playlist"""
    
    def __init__(self, playlist_repository):
        self.playlist_repository = playlist_repository
    
    async def execute(
        self,
        user_id: str,
        playlist_id: str,
        collaborator_id: str
    ) -> Dict[str, Any]:
        """Remove collaborator from playlist"""
        # Check playlist exists and user is owner
        playlist = await self.playlist_repository.get_by_id(playlist_id)
        if not playlist:
            raise ValidationError("Playlist not found")
        
        if playlist.owner_id != user_id:
            raise AuthenticationError("Only playlist owner can remove collaborators")
        
        # Remove collaborator
        success = await self.playlist_repository.remove_collaborator(playlist_id, collaborator_id)
        
        if not success:
            raise ValidationError("Failed to remove collaborator")
        
        return {"status": "success", "removed_user_id": collaborator_id}
