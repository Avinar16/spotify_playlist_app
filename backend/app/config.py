import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://spotify_user:spotify_password@localhost:5432/spotify_playlist_db"
    
    # JWT
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    JWT_REFRESH_EXPIRATION_DAYS: int = 7
    
    # Spotify API
    SPOTIFY_CLIENT_ID: str = "28cd22a51fff4f499901583a60f5a937"
    SPOTIFY_CLIENT_SECRET: str = "46a4a05fab674c0d81e32f6d21b3955b"
    SPOTIFY_REDIRECT_URI: str = "http://127.0.0.1:8000/api/spotify/callback"
    
    # App
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    APP_TITLE: str = "Spotify Playlist Generator"
    APP_VERSION: str = "0.1.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
