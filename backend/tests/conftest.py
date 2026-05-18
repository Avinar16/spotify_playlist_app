"""Pytest configuration and fixtures"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.infrastructure.database.models import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """Create in-memory SQLite database session for testing"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def mock_spotify_client():
    """Create mock Spotify client"""
    client = AsyncMock()
    client.get_current_user = AsyncMock(return_value={
        "id": "test_user_123",
        "display_name": "Test User",
        "email": "test@example.com"
    })
    client.get_top_artists = AsyncMock(return_value=[
        {"name": "Artist 1", "id": "1"},
        {"name": "Artist 2", "id": "2"},
    ])
    client.search_tracks = AsyncMock(return_value=[
        {
            "id": "track_1",
            "name": "Track 1",
            "artist": "Artist 1",
            "album": "Album 1",
            "duration_ms": 180000,
            "preview_url": None
        }
    ])
    return client


@pytest.fixture
def mock_lastfm_client():
    """Create mock Last.fm client"""
    client = AsyncMock()
    client.get_similar_artists = AsyncMock(return_value=["Similar Artist 1", "Similar Artist 2"])
    client.get_similar_artists_with_score = AsyncMock(return_value=[
        ("Similar Artist 1", 0.8),
        ("Similar Artist 2", 0.6),
    ])
    client.get_top_tracks = AsyncMock(return_value=[
        {"title": "Top Track 1", "artist": "Artist 1"},
        {"title": "Top Track 2", "artist": "Artist 1"},
    ])
    client.get_mixed_tracks = AsyncMock(return_value=[
        {"title": "Mixed Track 1", "artist": "Artist 1"},
        {"title": "Mixed Track 2", "artist": "Artist 1"},
    ])
    return client
