import logging

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_list_delimiter=",",
        extra="ignore",
    )

    ENVIRONMENT: str = "development"

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
    SPOTIFY_REDIRECT_URI: str = ""
    CORS_ORIGINS: str = ""

    def get_cors_origins(self) -> list[str]:
        if not self.CORS_ORIGINS:
            return []
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Encryption
    ENCRYPTION_KEY: str

    # Last.fm
    LASTFM_KEY: str
    LASTFM_SHARED: str

    # App
    DEBUG: bool = True
    APP_TITLE: str = "Spotify Playlist Generator"
    APP_VERSION: str = "0.1.0"

    @model_validator(mode="after")
    def compute_derived_settings(self) -> "Settings":
        if self.ENVIRONMENT == "development":
            self.SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8000/api/spotify/callback"
            if not self.CORS_ORIGINS:
                self.CORS_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:3000"
        else:
            if not self.SPOTIFY_REDIRECT_URI:
                raise ValueError("SPOTIFY_REDIRECT_URI must be provided in production!")
            if not self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS must be provided in production!")
        return self


settings = Settings()
