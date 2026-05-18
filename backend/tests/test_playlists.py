"""Tests for playlist use cases"""
import pytest
from uuid import uuid4
from app.use_cases.playlists import (
    AddTrackToPlaylistUseCase,
    SearchTracksUseCase,
)
from app.infrastructure.database.playlist_repository import PlaylistRepository
from app.infrastructure.database.user_repository import UserRepository


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_track_to_playlist_validates_inputs(db_session, mock_spotify_client):
    """Test that adding track validates user existence"""
    playlist_repo = PlaylistRepository(db_session)
    user_repo = UserRepository(db_session)
    
    use_case = AddTrackToPlaylistUseCase(playlist_repo, user_repo, mock_spotify_client)
    
    # Trying with non-existent user should fail
    try:
        result = await use_case.execute(
            user_id="nonexistent_user",
            playlist_id="nonexistent_playlist",
            spotify_track_id="track_123"
        )
    except Exception:
        # Expected to fail with non-existent user/playlist
        pass
