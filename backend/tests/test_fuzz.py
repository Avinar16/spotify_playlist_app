import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from hypothesis import assume, given, settings as h_settings, HealthCheck
from hypothesis import strategies as st

from app.core.exceptions import AuthenticationError, ValidationError
from app.infrastructure.database.encrypted_type import EncryptedText
from app.interfaces.http.routes import PlaylistUpdate
from app.interfaces.schemas import PlaylistCreate
from app.use_cases.auth import LoginUserUseCase, RefreshTokenUseCase, RegisterUserUseCase
from app.use_cases.playlists import (
    AddTrackToPlaylistUseCase,
    GeneratePlaylistFromBridgeUseCase,
    InviteCollaboratorUseCase,
    SearchTracksUseCase,
)

_TEST_FERNET_KEY = Fernet.generate_key().decode()

ALLOWED = (ValidationError, AuthenticationError)


# Helpers


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
# SearchTracksUseCase
# ---------------------------------------------------------------------------

@given(st.text())
@h_settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_search_tracks_never_crashes(query):
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
@h_settings(max_examples=200, deadline=None)
def test_search_tracks_short_query_raises_validation_error(query):
    assume(len(query.strip()) < 2)

    user_repo = AsyncMock()
    user_repo.get_by_id = AsyncMock(return_value=_user())
    uc = SearchTracksUseCase(AsyncMock(), user_repo)

    async def go():
        with pytest.raises(ValidationError):
            await uc.execute(user_id="user-123", query=query, limit=20)

    run(go())


# ---------------------------------------------------------------------------
# AddTrackToPlaylistUseCase
# ---------------------------------------------------------------------------

@given(st.text())
@h_settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_add_track_never_crashes(track_id):
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
@h_settings(max_examples=100, deadline=None)
def test_add_track_empty_id_raises_validation_error(track_id):
    assume(not track_id or not track_id.strip())

    pl_repo = AsyncMock()
    pl_repo.get_by_id = AsyncMock(return_value=_playlist())
    uc = AddTrackToPlaylistUseCase(pl_repo, AsyncMock(), AsyncMock())

    async def go():
        with pytest.raises(ValidationError):
            await uc.execute(user_id="user-123", playlist_id="pl-1", spotify_track_id=track_id)

    run(go())


# ---------------------------------------------------------------------------
# InviteCollaboratorUseCase
# ---------------------------------------------------------------------------

@given(st.text())
@h_settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_invite_collaborator_never_crashes(search_query):
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
@h_settings(max_examples=100, deadline=None)
def test_invite_empty_query_raises_validation_error(search_query):
    assume(not search_query or not search_query.strip())

    uc = InviteCollaboratorUseCase(AsyncMock(), AsyncMock())

    async def go():
        with pytest.raises(ValidationError):
            await uc.execute(user_id="user-123", playlist_id="pl-1", search_query=search_query)

    run(go())


# ---------------------------------------------------------------------------
# GeneratePlaylistFromBridgeUseCase
# ---------------------------------------------------------------------------

@given(st.integers())
@h_settings(max_examples=300, deadline=None)
def test_generate_playlist_out_of_range_quantity(quantity):
    assume(quantity < 5 or quantity > 30)

    uc = GeneratePlaylistFromBridgeUseCase(AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock())

    async def go():
        with pytest.raises(ValidationError):
            await uc.execute(user_id="user-123", playlist_id="pl-1", quantity=quantity)

    run(go())


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

@given(name=st.text(), description=st.one_of(st.none(), st.text()))
@h_settings(max_examples=500, deadline=None)
def test_playlist_create_schema(name, description):
    try:
        PlaylistCreate(name=name, description=description)
    except Exception:
        pass


@given(name=st.text(), description=st.one_of(st.none(), st.text()))
@h_settings(max_examples=500, deadline=None)
def test_playlist_update_schema(name, description):
    try:
        PlaylistUpdate(name=name, description=description)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# SearchTracksUseCase — limit parameter
# ---------------------------------------------------------------------------

@given(limit=st.integers())
@h_settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_search_tracks_any_limit_never_crashes(limit):
    user_repo = AsyncMock()
    user_repo.get_by_id = AsyncMock(return_value=_user())

    spotify = AsyncMock()
    spotify.search_tracks = AsyncMock(return_value=[])

    uc = SearchTracksUseCase(spotify, user_repo)

    async def go():
        try:
            await uc.execute(user_id="user-123", query="valid query", limit=limit)
        except ALLOWED:
            pass

    run(go())


# ---------------------------------------------------------------------------
# RegisterUserUseCase
# ---------------------------------------------------------------------------

@given(email=st.text(), username=st.text(), password=st.text())
@h_settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_register_never_crashes(email, username, password):
    user_repo = AsyncMock()
    user_repo.get_by_email = AsyncMock(return_value=None)
    user_repo.get_by_username = AsyncMock(return_value=None)
    user_repo.create = AsyncMock(return_value=MagicMock(
        id="u1", email="a@b.com", username="u",
        created_at=datetime.datetime.utcnow(),
    ))

    uc = RegisterUserUseCase(user_repo)

    async def go():
        try:
            await uc.execute(email=email, username=username, password=password)
        except ALLOWED:
            pass

    run(go())


@given(password=st.text(max_size=7))
@h_settings(max_examples=200, deadline=None)
def test_register_short_password_raises_validation_error(password):
    assume(len(password) < 8)

    uc = RegisterUserUseCase(AsyncMock())

    async def go():
        with pytest.raises(ValidationError):
            await uc.execute(email="valid@email.com", username="user", password=password)

    run(go())


@given(email=st.text(alphabet=st.characters(blacklist_characters="@")))
@h_settings(max_examples=200, deadline=None)
def test_register_email_without_at_raises_validation_error(email):
    uc = RegisterUserUseCase(AsyncMock())

    async def go():
        with pytest.raises(ValidationError):
            await uc.execute(email=email, username="user", password="validpass123")

    run(go())


# ---------------------------------------------------------------------------
# LoginUserUseCase
# ---------------------------------------------------------------------------

@given(email=st.text(), password=st.text())
@h_settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_login_never_crashes(email, password):
    user_repo = AsyncMock()
    user_repo.get_by_email = AsyncMock(return_value=None)

    uc = LoginUserUseCase(user_repo)

    async def go():
        try:
            await uc.execute(email=email, password=password)
        except ALLOWED:
            pass

    run(go())


# ---------------------------------------------------------------------------
# RefreshTokenUseCase
# ---------------------------------------------------------------------------

@given(token=st.text())
@h_settings(max_examples=300, deadline=None)
def test_refresh_token_never_crashes(token):
    user_repo = AsyncMock()
    user_repo.get_by_id = AsyncMock(return_value=None)

    uc = RefreshTokenUseCase(user_repo)

    async def go():
        try:
            await uc.execute(refresh_token=token)
        except ALLOWED:
            pass

    run(go())


# ---------------------------------------------------------------------------
# EncryptedText
# ---------------------------------------------------------------------------

@given(plaintext=st.text())
@h_settings(max_examples=500, deadline=None)
def test_encryption_roundtrip_arbitrary_text(plaintext):
    with patch("app.infrastructure.database.encrypted_type.settings") as mock_s:
        mock_s.ENCRYPTION_KEY = _TEST_FERNET_KEY
        et = EncryptedText()
        encrypted = et.process_bind_param(plaintext, None)
        assert isinstance(encrypted, str)
        decrypted = et.process_result_value(encrypted, None)
        assert decrypted == plaintext


@given(value=st.text())
@h_settings(max_examples=300, deadline=None)
def test_decrypt_arbitrary_string_never_crashes(value):
    with patch("app.infrastructure.database.encrypted_type.settings") as mock_s:
        mock_s.ENCRYPTION_KEY = _TEST_FERNET_KEY
        et = EncryptedText()
        result = et.process_result_value(value, None)
        assert result is None or isinstance(result, str)


@given(plaintext=st.text(min_size=1000, max_size=10000))
@h_settings(max_examples=50, deadline=None)
def test_encryption_roundtrip_long_strings(plaintext):
    with patch("app.infrastructure.database.encrypted_type.settings") as mock_s:
        mock_s.ENCRYPTION_KEY = _TEST_FERNET_KEY
        et = EncryptedText()
        decrypted = et.process_result_value(et.process_bind_param(plaintext, None), None)
        assert decrypted == plaintext
