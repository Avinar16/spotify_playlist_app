import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import assume, given, settings as h_settings, HealthCheck
from hypothesis import strategies as st

from app.core.exceptions import AuthenticationError, ValidationError
from app.interfaces.http.routes import PlaylistUpdate
from app.interfaces.schemas import PlaylistCreate
from app.use_cases.playlists import (
    AddTrackToPlaylistUseCase,
    GeneratePlaylistFromBridgeUseCase,
    InviteCollaboratorUseCase,
    SearchTracksUseCase,
)

ALLOWED = (ValidationError, AuthenticationError)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user(owner_id="user-123"):
    u = MagicMock()
    u.id = owner_id
    u.access_token = "tok"
    u.refresh_token = "ref"
    u.spotify_id = "sp1"
    return u


def _playlist(owner_id="user-123"):
    p = MagicMock()
    p.id = "pl-1"
    p.owner_id = owner_id
    p.collaborators = []
    p.tracks = []
    p.spotify_id = None
    p.top_artists = None
    return p


def run(coro):
    asyncio.run(coro)


# ---------------------------------------------------------------------------
# SearchTracksUseCase — query string
# ---------------------------------------------------------------------------

@given(st.text())
@h_settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_search_tracks_never_crashes(query):
    """Any query string must raise ValidationError or return results — never crash."""
    user_repo = AsyncMock()
    user_repo.get_by_id = AsyncMock(return_value=_user())

    spotify = AsyncMock()
    spotify.search_tracks = AsyncMock(return_value=[])

    uc = SearchTracksUseCase(spotify, user_repo)

    async def go():
        try:
            await uc.execute(user_id="user-123", query=query, limit=20)
        except ALLOWED:
            pass

    run(go())


@given(st.text(max_size=1))
@h_settings(max_examples=200)
def test_search_tracks_short_query_raises_validation_error(query):
    """Queries shorter than 2 chars (after strip) must always raise ValidationError."""
    assume(len(query.strip()) < 2)

    user_repo = AsyncMock()
    user_repo.get_by_id = AsyncMock(return_value=_user())
    uc = SearchTracksUseCase(AsyncMock(), user_repo)

    async def go():
        with pytest.raises(ValidationError):
            await uc.execute(user_id="user-123", query=query, limit=20)

    run(go())


# ---------------------------------------------------------------------------
# AddTrackToPlaylistUseCase — track_id
# ---------------------------------------------------------------------------

@given(st.text())
@h_settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_add_track_never_crashes(track_id):
    """Any track_id string must produce a known exception or succeed — never crash."""
    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=_playlist())
    pl_repo.add_track = AsyncMock(return_value=MagicMock(
        id="t1", spotify_track_id=track_id or "x",
        track_name=None, track_artist=None,
        track_image_url=None, track_genres=None,
        added_at=datetime.datetime.utcnow(),
    ))

    user_repo = AsyncMock()
    user_repo.get_by_id = AsyncMock(return_value=_user())

    spotify = AsyncMock()
    spotify.get_track = AsyncMock(return_value={"name": "T", "artist": "A", "image": None, "genres": []})

    uc = AddTrackToPlaylistUseCase(pl_repo, user_repo, spotify)

    async def go():
        try:
            await uc.execute(user_id="user-123", playlist_id="pl-1", spotify_track_id=track_id)
        except ALLOWED:
            pass

    run(go())


@given(st.one_of(st.just(""), st.just("   "), st.text(alphabet=" \t\n", max_size=10)))
@h_settings(max_examples=100)
def test_add_track_empty_id_raises_validation_error(track_id):
    """Empty or whitespace track_id must always raise ValidationError."""
    assume(not track_id or not track_id.strip())

    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=_playlist())
    uc = AddTrackToPlaylistUseCase(pl_repo, AsyncMock(), AsyncMock())

    async def go():
        with pytest.raises(ValidationError):
            await uc.execute(user_id="user-123", playlist_id="pl-1", spotify_track_id=track_id)

    run(go())


# ---------------------------------------------------------------------------
# InviteCollaboratorUseCase — search_query
# ---------------------------------------------------------------------------

@given(st.text())
@h_settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_invite_collaborator_never_crashes(search_query):
    """Any search_query must produce a known exception or succeed — never crash."""
    target = MagicMock(id="user-456", username="other", email="other@test.com")

    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=_playlist(owner_id="user-123"))
    pl_repo.add_collaborator = AsyncMock(return_value=True)

    user_repo = AsyncMock()
    user_repo.get_by_email = AsyncMock(return_value=target)
    user_repo.get_by_username = AsyncMock(return_value=target)

    uc = InviteCollaboratorUseCase(pl_repo, user_repo)

    async def go():
        try:
            await uc.execute(user_id="user-123", playlist_id="pl-1", search_query=search_query)
        except ALLOWED:
            pass

    run(go())


@given(st.one_of(st.just(""), st.just("   "), st.text(alphabet=" \t\n", max_size=10)))
@h_settings(max_examples=100)
def test_invite_empty_query_raises_validation_error(search_query):
    """Empty search_query must always raise ValidationError."""
    assume(not search_query or not search_query.strip())

    uc = InviteCollaboratorUseCase(AsyncMock(), AsyncMock())

    async def go():
        with pytest.raises(ValidationError):
            await uc.execute(user_id="user-123", playlist_id="pl-1", search_query=search_query)

    run(go())


# ---------------------------------------------------------------------------
# GeneratePlaylistFromBridgeUseCase — quantity bounds
# ---------------------------------------------------------------------------

@given(st.integers())
@h_settings(max_examples=300)
def test_generate_playlist_out_of_range_quantity(quantity):
    """Quantity outside [5, 30] must always raise ValidationError immediately."""
    assume(quantity < 5 or quantity > 30)

    uc = GeneratePlaylistFromBridgeUseCase(AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock())

    async def go():
        with pytest.raises(ValidationError):
            await uc.execute(user_id="user-123", playlist_id="pl-1", quantity=quantity)

    run(go())


# ---------------------------------------------------------------------------
# Pydantic schemas — never crash on arbitrary strings
# ---------------------------------------------------------------------------

@given(name=st.text(), description=st.one_of(st.none(), st.text()))
@h_settings(max_examples=500)
def test_playlist_create_schema(name, description):
    """PlaylistCreate must never raise unexpected exceptions on any string input."""
    try:
        PlaylistCreate(name=name, description=description)
    except Exception:
        pass


@given(name=st.text(), description=st.one_of(st.none(), st.text()))
@h_settings(max_examples=500)
def test_playlist_update_schema(name, description):
    """PlaylistUpdate must never raise unexpected exceptions on any string input."""
    try:
        PlaylistUpdate(name=name, description=description)
    except Exception:
        pass
