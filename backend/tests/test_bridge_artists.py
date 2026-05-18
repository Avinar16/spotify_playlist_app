"""Tests for Bridge Artists functionality"""
import pytest
from unittest.mock import AsyncMock
from app.use_cases.playlists import FindBridgeArtistsUseCase
from uuid import uuid4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_bridge_artists_basic(mock_lastfm_client):
    """Test finding bridge artists between two users"""
    # Mock repositories
    playlist_repo = AsyncMock()
    user_repo = AsyncMock()
    
    # Create mock playlist with 2 users
    playlist = AsyncMock()
    playlist.id = str(uuid4())
    playlist.owner_id = "user1"
    
    playlist_repo.get_by_id = AsyncMock(return_value=playlist)
    playlist_repo.get_collaborators = AsyncMock(return_value=[
        type('User', (), {'id': 'user2', 'top_artists': '["Artist 2", "Artist 3"]'})()
    ])
    
    owner = type('User', (), {
        'id': 'user1',
        'top_artists': '["Artist 1", "Artist 2"]'
    })()
    
    user_repo.get_by_id = AsyncMock(return_value=owner)
    
    # Create use case
    use_case = FindBridgeArtistsUseCase(
        mock_lastfm_client,
        playlist_repo,
        user_repo,
        bridge_artist_repository=None
    )
    
    # Execute
    result = await use_case.execute(
        user_id="user1",
        playlist_id=playlist.id,
        limit=10,
        use_cache=False
    )
    
    # Verify
    assert isinstance(result, list)
    assert all(isinstance(item, tuple) for item in result)
    assert all(len(item) == 2 for item in result)  # (artist_name, score)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_bridge_artists_uses_cache(mock_lastfm_client):
    """Test that bridge artists use cache when available"""
    playlist_repo = AsyncMock()
    user_repo = AsyncMock()
    bridge_artist_repo = AsyncMock()
    
    playlist = AsyncMock()
    playlist.id = "playlist_123"
    playlist.owner_id = "user1"
    
    playlist_repo.get_by_id = AsyncMock(return_value=playlist)
    
    # Mock cached bridge artists
    cached_artists = [("Bridge Artist 1", 0.9), ("Bridge Artist 2", 0.7)]
    bridge_artist_repo.get_bridge_artists = AsyncMock(return_value=cached_artists)
    
    use_case = FindBridgeArtistsUseCase(
        mock_lastfm_client,
        playlist_repo,
        user_repo,
        bridge_artist_repository=bridge_artist_repo
    )
    
    # Execute with cache enabled
    result = await use_case.execute(
        user_id="user1",
        playlist_id="playlist_123",
        limit=10,
        use_cache=True
    )
    
    # Should return cached results without calling get_collaborators
    assert result == cached_artists
    bridge_artist_repo.get_bridge_artists.assert_called_once()
    playlist_repo.get_collaborators.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_bridge_artists_no_top_artists(mock_lastfm_client):
    """Test handling when users have no top artists"""
    playlist_repo = AsyncMock()
    user_repo = AsyncMock()
    
    playlist = AsyncMock()
    playlist.id = str(uuid4())
    playlist.owner_id = "user1"
    
    playlist_repo.get_by_id = AsyncMock(return_value=playlist)
    playlist_repo.get_collaborators = AsyncMock(return_value=[])
    
    owner = type('User', (), {
        'id': 'user1',
        'top_artists': None  # No top artists
    })()
    
    user_repo.get_by_id = AsyncMock(return_value=owner)
    
    use_case = FindBridgeArtistsUseCase(
        mock_lastfm_client,
        playlist_repo,
        user_repo,
        bridge_artist_repository=None
    )
    
    # Should raise ValidationError
    from app.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        await use_case.execute(
            user_id="user1",
            playlist_id=playlist.id,
            use_cache=False
        )
