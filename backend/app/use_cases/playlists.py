"""Playlist management use cases"""
import logging
import hashlib
import json
from typing import Optional, List, Dict, Any
from uuid import uuid4
from app.core.exceptions import ValidationError, AuthenticationError

logger = logging.getLogger(__name__)


def check_playlist_access(playlist, user_id: str) -> bool:
    """Check if user has access to playlist (owner or collaborator)"""
    if playlist.owner_id == user_id:
        return True
    return any(collab.id == user_id for collab in playlist.collaborators)


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

        if not check_playlist_access(playlist, user_id):
            raise AuthenticationError("You don't have permission to modify this playlist")

        # Get track details if spotify_client is provided
        track_name = None
        track_artist = None
        track_image_url = None
        track_genres = None

        if self.spotify_client:
            try:
                user = await self.user_repository.get_by_id(user_id)
                if user and user.access_token:
                    track_info = await self.spotify_client.get_track(user.access_token, spotify_track_id)
                    track_name = track_info.get("name")
                    track_artist = track_info.get("artist")
                    track_image_url = track_info.get("image")
                    # Store genres as JSON string
                    genres = track_info.get("genres", [])
                    if genres:
                        track_genres = json.dumps(genres)
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
                track_image_url=track_image_url,
                track_genres=track_genres
            )
            return {
                "id": track.id,
                "spotify_track_id": track.spotify_track_id,
                "track_name": track.track_name,
                "track_artist": track.track_artist,
                "track_image_url": track.track_image_url,
                "track_genres": json.loads(track.track_genres) if track.track_genres else [],
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

            if not check_playlist_access(playlist, user_id):
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
        """Get collaborators for playlist (including owner)"""
        # Check playlist exists and user has access
        playlist = await self.playlist_repository.get_by_id(playlist_id)
        if not playlist:
            raise ValidationError("Playlist not found")

        if not check_playlist_access(playlist, user_id):
            raise AuthenticationError("You don't have access to this playlist")

        # Get owner
        owner = await self.user_repository.get_by_id(playlist.owner_id)

        # Get other collaborators
        collaborators = await self.playlist_repository.get_collaborators(playlist_id)

        # Combine owner with collaborators
        all_members = []

        # Add owner first
        if owner:
            all_members.append({
                "id": owner.id,
                "username": owner.username,
                "email": owner.email,
                "is_owner": True
            })

        # Add collaborators
        for collab in collaborators:
            all_members.append({
                "id": collab.id,
                "username": collab.username,
                "email": collab.email,
                "is_owner": False
            })

        return all_members


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


class GetPlaylistStateUseCase:
    """Get playlist state with snapshot_id for real-time sync"""

    def __init__(self, playlist_repository):
        self.playlist_repository = playlist_repository

    def _generate_snapshot_id(self, playlist) -> str:
        """Generate hash of playlist state for change detection"""
        state_data = {
            "id": playlist.id,
            "name": playlist.name,
            "description": playlist.description,
            "tracks": [
                {"id": t.id, "spotify_id": t.spotify_track_id}
                for t in (playlist.tracks or [])
            ]
        }
        state_json = json.dumps(state_data, sort_keys=True)
        return hashlib.sha256(state_json.encode()).hexdigest()[:16]

    async def execute(
            self,
            user_id: str,
            playlist_id: str,
            last_snapshot_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get playlist state, optionally only if changed from last_snapshot_id"""
        # Check playlist exists and user has access
        playlist = await self.playlist_repository.get_by_id(playlist_id)
        if not playlist:
            raise ValidationError("Playlist not found")

        if not check_playlist_access(playlist, user_id):
            raise AuthenticationError("You don't have access to this playlist")

        # Generate current snapshot
        current_snapshot_id = self._generate_snapshot_id(playlist)

        # If client has same snapshot, return minimal response
        if last_snapshot_id and last_snapshot_id == current_snapshot_id:
            return {
                "changed": False,
                "snapshot_id": current_snapshot_id,
                "playlist": None
            }

        # Return full state if changed or no snapshot provided
        return {
            "changed": True,
            "snapshot_id": current_snapshot_id,
            "playlist": {
                "id": playlist.id,
                "name": playlist.name,
                "description": playlist.description,
                "owner_id": playlist.owner_id,
                "spotify_id": playlist.spotify_id,
                "tracks": [
                    {
                        "id": track.id,
                        "spotify_track_id": track.spotify_track_id,
                        "track_name": track.track_name,
                        "track_artist": track.track_artist,
                        "track_image_url": track.track_image_url,
                        "track_genres": json.loads(track.track_genres) if track.track_genres else [],
                        "added_at": track.added_at.isoformat()
                    }
                    for track in (playlist.tracks or [])
                ]
            }
        }


class DeleteTrackFromPlaylistUseCase:
    """Delete track from playlist"""

    def __init__(self, playlist_repository):
        self.playlist_repository = playlist_repository

    async def execute(
            self,
            user_id: str,
            playlist_id: str,
            track_id: str
    ) -> Dict[str, Any]:
        """Delete track from playlist"""
        # Check playlist exists and user has access
        playlist = await self.playlist_repository.get_by_id(playlist_id)
        if not playlist:
            raise ValidationError("Playlist not found")

        if not check_playlist_access(playlist, user_id):
            raise AuthenticationError("You don't have permission to modify this playlist")

        # Check track exists in playlist
        track = next((t for t in (playlist.tracks or []) if t.id == track_id), None)
        if not track:
            raise ValidationError("Track not found in playlist")

        # Delete track
        success = await self.playlist_repository.remove_track(track_id)

        if not success:
            raise ValidationError("Failed to remove track")

        return {"status": "success", "removed_track_id": track_id}


class DeletePlaylistUseCase:
    """Delete entire playlist"""

    def __init__(self, playlist_repository):
        self.playlist_repository = playlist_repository

    async def execute(
            self,
            user_id: str,
            playlist_id: str
    ) -> Dict[str, Any]:
        """Delete playlist (only owner can delete)"""
        # Check playlist exists and user is owner
        playlist = await self.playlist_repository.get_by_id(playlist_id)
        if not playlist:
            raise ValidationError("Playlist not found")

        # Delete playlist
        success = await self.playlist_repository.delete(playlist_id)

        return {"status": "success", "deleted_playlist_id": playlist_id}


class FindBridgeArtistsUseCase:
    """Find bridge artists between collaborators' tastes"""

    def __init__(self, lastfm_client, playlist_repository, user_repository, bridge_artist_repository=None):
        self.lastfm_client = lastfm_client
        self.playlist_repository = playlist_repository
        self.user_repository = user_repository
        self.bridge_artist_repository = bridge_artist_repository

    async def execute(
            self,
            user_id: str,
            playlist_id: str,
            limit: int = 50,
            use_cache: bool = True
    ) -> List[tuple[str, float]]:
        """
        Find bridge artists between all collaborators' tastes.
        Uses harmonic mean scoring and coverage weighting.
        Returns cached results if available.
        """
        import asyncio

        # Check playlist exists and user has access
        playlist = await self.playlist_repository.get_by_id(playlist_id)
        if not playlist:
            raise ValidationError("Playlist not found")

        if not check_playlist_access(playlist, user_id):
            raise AuthenticationError("You don't have access to this playlist")

        # Try to get cached bridge artists
        if use_cache and self.bridge_artist_repository:
            cached = await self.bridge_artist_repository.get_bridge_artists(playlist_id)
            if cached:
                logger.info(f"Using cached bridge artists for playlist {playlist_id}")
                return cached[:limit]

        # Calculate bridge artists

        # Get all collaborators (owner + collaborators)
        owner = await self.user_repository.get_by_id(playlist.owner_id)
        collaborators = await self.playlist_repository.get_collaborators(playlist_id)

        all_users = [owner] + collaborators
        users_artists = []

        # Collect top artists from all collaborators
        for user in all_users:
            if not user.top_artists:
                logger.warning(f"User {user.id} has no top artists recorded")
                continue

            try:
                artists = json.loads(user.top_artists)
                users_artists.append(artists)
            except Exception as e:
                logger.warning(f"Failed to parse top artists for user {user.id}: {e}")

        if not users_artists:
            raise ValidationError("No collaborators with top artists available")

        # Get all known artists
        known_artists = set()
        for user_artists in users_artists:
            known_artists.update(user_artists)

        # Fetch similar artists for each user's artists
        user_similar_maps = []
        for user_artists in users_artists:
            similar_map = {}
            tasks = [self.lastfm_client.get_similar_artists_with_score(a, limit=20) for a in user_artists]
            results = await asyncio.gather(*tasks)

            for similar_list in results:
                for artist, score in similar_list:
                    similar_map[artist] = max(similar_map.get(artist, 0), score)

            user_similar_maps.append(similar_map)

        # Calculate bridge scores using harmonic mean
        all_candidates = set()
        for similar_map in user_similar_maps:
            all_candidates.update(similar_map.keys())
        all_candidates.update(known_artists)

        bridge_scores = {}
        for artist in all_candidates:
            scores_per_user = [similar_map.get(artist, 0) for similar_map in user_similar_maps]

            if all(s > 0 for s in scores_per_user):
                # All users know this artist (directly or via similarity)
                n = len(scores_per_user)
                harmonic = n / sum(1 / s for s in scores_per_user)
            else:
                # Some users don't know this artist
                non_zero = [s for s in scores_per_user if s > 0]
                if not non_zero:
                    continue
                coverage = len(non_zero) / len(scores_per_user)
                harmonic = (len(non_zero) / sum(1 / s for s in non_zero)) * (coverage ** 2)

            # Penalty for known artists to encourage discovery
            if artist in known_artists:
                harmonic *= 0.5

            bridge_scores[artist] = harmonic

        # Sort by score and return top N
        result = sorted(bridge_scores.items(), key=lambda x: x[1], reverse=True)[:limit]

        # Cache the results
        if self.bridge_artist_repository:
            try:
                await self.bridge_artist_repository.save_bridge_artists(playlist_id, result)
            except Exception as e:
                logger.warning(f"Failed to cache bridge artists for playlist {playlist_id}: {e}")

        return result


class GeneratePlaylistFromBridgeUseCase:
    """Generate playlist using bridge artists and Last.fm tracks"""

    def __init__(self, spotify_client, lastfm_client, playlist_repository, user_repository):
        self.spotify_client = spotify_client
        self.lastfm_client = lastfm_client
        self.playlist_repository = playlist_repository
        self.user_repository = user_repository

    def _limit_tracks_per_artist(
            self,
            tracks_by_artist: Dict[str, list[dict]],
            artist_scores: Dict[str, float],
            total_tracks: int = 20,
            min_per_artist: int = 1,
            max_per_artist: int = 4
    ) -> list[dict]:
        """Distribute track quota proportional to bridge score"""
        total_score = sum(artist_scores.get(a, 0) for a in tracks_by_artist)

        if total_score == 0:
            total_score = 1

        quotas = {}
        for artist in tracks_by_artist:
            score = artist_scores.get(artist, 0)
            raw_quota = (score / total_score) * total_tracks
            quotas[artist] = max(min_per_artist, min(max_per_artist, round(raw_quota)))

        result = []
        for artist, tracks in tracks_by_artist.items():
            quota = quotas[artist]
            result.extend(tracks[:quota])

        return result

    async def execute(
            self,
            user_id: str,
            playlist_id: str,
            quantity: int = 20
    ) -> Dict[str, Any]:
        """
        Generate and add tracks to playlist based on bridge artists.
        Gets mixed tracks (60% top + 40% random) from Last.fm for each bridge artist.
        Limits tracks per artist to 1-4 based on artist score.
        """
        import asyncio

        if quantity < 5 or quantity > 30:
            raise ValidationError("Quantity must be between 5 and 30")

        # Check playlist exists and user has access
        playlist = await self.playlist_repository.get_by_id(playlist_id)
        if not playlist:
            raise ValidationError("Playlist not found")

        if not check_playlist_access(playlist, user_id):
            raise AuthenticationError("You don't have access to modify this playlist")

        # Get user's Spotify token
        user = await self.user_repository.get_by_id(user_id)
        if not user or not user.access_token:
            raise AuthenticationError("Spotify account not linked")

        # Find bridge artists
        bridge_use_case = FindBridgeArtistsUseCase(self.lastfm_client, self.playlist_repository, self.user_repository)
        bridge_artists = await bridge_use_case.execute(user_id, playlist_id, limit=20)

        if not bridge_artists:
            raise ValidationError("Could not find bridge artists")

        # Extract artist names and scores
        artist_names = [artist[0] for artist in bridge_artists]
        artist_scores = {artist[0]: artist[1] for artist in bridge_artists}

        logger.info(f"Found {len(artist_names)} bridge artists for playlist {playlist_id}")

        # Get mixed tracks (60% top + 40% random) from Last.fm for each bridge artist
        tracks_by_artist = {}
        tasks = [self.lastfm_client.get_mixed_tracks(artist, limit=6) for artist in artist_names]
        results = await asyncio.gather(*tasks)

        for artist_name, tracks_list in zip(artist_names, results):
            if tracks_list:
                tracks_by_artist[artist_name] = tracks_list

        logger.info(f"Got mixed tracks from {len(tracks_by_artist)} bridge artists")

        if not tracks_by_artist:
            raise ValidationError("Could not find tracks from bridge artists")

        # Apply artist quota limits (1-4 tracks per artist based on score)
        limited_tracks = self._limit_tracks_per_artist(
            tracks_by_artist,
            artist_scores,
            total_tracks=quantity,
            min_per_artist=1,
            max_per_artist=4
        )

        logger.info(f"Limited to {len(limited_tracks)} total tracks across artists")

        # Search for tracks on Spotify and add to playlist
        added_tracks = []

        for track_candidate in limited_tracks:
            if len(added_tracks) >= quantity:
                break

            try:
                # Search for track on Spotify
                query = f"{track_candidate['title']} {track_candidate['artist']}"
                search_results = await self.spotify_client.search_tracks(
                    access_token=user.access_token,
                    query=query,
                    limit=1
                )

                if not search_results:
                    logger.debug(f"Track not found on Spotify: {query}")
                    continue

                track = search_results[0]
                spotify_track_id = track.get("id")
                track_name = track.get("name")
                track_artist = track.get("artist")
                track_image_url = track.get("image")

                # Add track to playlist
                added_track = await self.playlist_repository.add_track(
                    playlist_id=playlist_id,
                    spotify_track_id=spotify_track_id,
                    added_by_id=user_id,
                    track_name=track_name,
                    track_artist=track_artist,
                    track_image_url=track_image_url,
                    track_genres=None
                )

                added_tracks.append({
                    "id": added_track.id,
                    "spotify_track_id": spotify_track_id,
                    "track_name": track_name,
                    "track_artist": track_artist,
                    "track_image_url": track_image_url
                })

            except Exception as e:
                logger.warning(f"Failed to add track {track_candidate}: {str(e)}")

        return {
            "status": "success",
            "playlist_id": playlist_id,
            "bridge_artists_used": len(tracks_by_artist),
            "tracks_added": len(added_tracks),
            "tracks": added_tracks
        }
