import os
import logging
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 720  # 30 days
    JWT_REFRESH_EXPIRATION_DAYS: int = 60
    
    # Spotify API
    SPOTIFY_CLIENT_ID: str
    SPOTIFY_CLIENT_SECRET: str
    SPOTIFY_REDIRECT_URI: str

    LASTFM_KEY: str
    LASTFM_SHARED: str
    
    # App
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    APP_TITLE: str = "Spotify Playlist Generator"
    APP_VERSION: str = "0.1.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
