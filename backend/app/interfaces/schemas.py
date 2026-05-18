from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    created_at: datetime
    spotify_id: Optional[str] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PlaylistCreate(BaseModel):
    name: str
    description: Optional[str] = None


class PlaylistTrackResponse(BaseModel):
    id: str
    spotify_track_id: str
    track_name: Optional[str] = None
    track_artist: Optional[str] = None
    track_image_url: Optional[str] = None
    added_by_id: str
    added_at: datetime

    class Config:
        from_attributes = True


class PlaylistResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    owner_id: str
    spotify_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PlaylistDetailResponse(PlaylistResponse):
    tracks: list[PlaylistTrackResponse]


class HealthResponse(BaseModel):
    status: str
    message: str
    database: str


class GenresResponse(BaseModel):
    genres: list[str]
    count: int
