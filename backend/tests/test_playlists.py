import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.core.exceptions import AuthenticationError, ValidationError
from app.use_cases.playlists import (
    AddTrackToPlaylistUseCase,
    DeleteTrackFromPlaylistUseCase,
    DeletePlaylistUseCase,
    SearchTracksUseCase,
)


def _make_user(user_id="user-1"):
    u = MagicMock()
    u.id = user_id
    u.access_token = "tok"
    u.refresh_token = "ref"
    u.spotify_id = "sp1"
    return u


def _make_playlist(owner_id="user-1", tracks=None):
    p = MagicMock()
    p.id = "pl-1"
    p.owner_id = owner_id
    p.collaborators = []
    p.tracks = tracks or []
    p.spotify_id = None
    return p


def _make_track(track_id="track-1", playlist_id="pl-1"):
    t = MagicMock()
    t.id = track_id
    t.playlist_id = playlist_id
    t.spotify_track_id = "sp-track-1"
    t.track_name = "Song"
    t.track_artist = "Artist"
    t.track_image_url = None
    t.track_genres = None
    t.added_at = datetime.datetime.utcnow()
    return t



@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tracks_success(mock_spotify_client):
    user_repo = AsyncMock()
    user_repo.get_by_id = AsyncMock(return_value=_make_user())

    uc = SearchTracksUseCase(mock_spotify_client, user_repo)
    result = await uc.execute(user_id="user-1", query="rock", limit=5)

    assert isinstance(result, list)
    mock_spotify_client.search_tracks.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tracks_short_query_raises():
    uc = SearchTracksUseCase(AsyncMock(), AsyncMock())
    with pytest.raises(ValidationError):
        await uc.execute(user_id="user-1", query="a", limit=5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tracks_no_spotify_token():
    user = _make_user()
    user.access_token = None
    user_repo = AsyncMock()
    user_repo.get_by_id = AsyncMock(return_value=user)

    uc = SearchTracksUseCase(AsyncMock(), user_repo)
    with pytest.raises(AuthenticationError):
        await uc.execute(user_id="user-1", query="rock", limit=5)



@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_track_success(mock_spotify_client):
    track = _make_track()
    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=_make_playlist())
    pl_repo.add_track = AsyncMock(return_value=track)

    user_repo = AsyncMock()
    user_repo.get_by_id = AsyncMock(return_value=_make_user())

    uc = AddTrackToPlaylistUseCase(pl_repo, user_repo, mock_spotify_client)
    result = await uc.execute(user_id="user-1", playlist_id="pl-1", spotify_track_id="sp-track-1")

    assert result["spotify_track_id"] == track.spotify_track_id
    pl_repo.add_track.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_track_empty_id_raises():
    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=_make_playlist())

    uc = AddTrackToPlaylistUseCase(pl_repo, AsyncMock(), AsyncMock())
    with pytest.raises(ValidationError):
        await uc.execute(user_id="user-1", playlist_id="pl-1", spotify_track_id="   ")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_track_access_denied():
    """User who is neither owner nor collaborator cannot add track."""
    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=_make_playlist(owner_id="other-user"))

    uc = AddTrackToPlaylistUseCase(pl_repo, AsyncMock(), AsyncMock())
    with pytest.raises(AuthenticationError):
        await uc.execute(user_id="user-1", playlist_id="pl-1", spotify_track_id="sp-track-1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_track_collaborator_allowed(mock_spotify_client):
    """Collaborator can add a track."""
    collaborator = MagicMock()
    collaborator.id = "user-1"
    playlist = _make_playlist(owner_id="other-user")
    playlist.collaborators = [collaborator]

    track = _make_track()
    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=playlist)
    pl_repo.add_track = AsyncMock(return_value=track)

    user_repo = AsyncMock()
    user_repo.get_by_id = AsyncMock(return_value=_make_user())

    uc = AddTrackToPlaylistUseCase(pl_repo, user_repo, mock_spotify_client)
    result = await uc.execute(user_id="user-1", playlist_id="pl-1", spotify_track_id="sp-track-1")

    assert result["spotify_track_id"] == track.spotify_track_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_track_playlist_not_found():
    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=None)

    uc = AddTrackToPlaylistUseCase(pl_repo, AsyncMock(), AsyncMock())
    with pytest.raises(ValidationError):
        await uc.execute(user_id="user-1", playlist_id="pl-1", spotify_track_id="sp-track-1")



@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_track_success():
    track = _make_track()
    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=_make_playlist(tracks=[track]))
    pl_repo.remove_track = AsyncMock(return_value=True)

    uc = DeleteTrackFromPlaylistUseCase(pl_repo)
    result = await uc.execute(user_id="user-1", playlist_id="pl-1", track_id="track-1")

    assert result["removed_track_id"] == "track-1"
    pl_repo.remove_track.assert_called_once_with("track-1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_track_access_denied():
    track = _make_track()
    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=_make_playlist(owner_id="other-user", tracks=[track]))

    uc = DeleteTrackFromPlaylistUseCase(pl_repo)
    with pytest.raises(AuthenticationError):
        await uc.execute(user_id="user-1", playlist_id="pl-1", track_id="track-1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_track_not_in_playlist():
    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=_make_playlist(tracks=[]))

    uc = DeleteTrackFromPlaylistUseCase(pl_repo)
    with pytest.raises(ValidationError):
        await uc.execute(user_id="user-1", playlist_id="pl-1", track_id="nonexistent")



@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_playlist_success():
    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=_make_playlist())
    pl_repo.delete = AsyncMock(return_value=True)

    uc = DeletePlaylistUseCase(pl_repo)
    result = await uc.execute(user_id="user-1", playlist_id="pl-1")

    assert result["deleted_playlist_id"] == "pl-1"
    pl_repo.delete.assert_called_once_with("pl-1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_playlist_not_found():
    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=None)

    uc = DeletePlaylistUseCase(pl_repo)
    with pytest.raises(ValidationError):
        await uc.execute(user_id="user-1", playlist_id="pl-1")
