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

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PlaylistCreate(BaseModel):
    name: str
    description: Optional[str] = None


class PlaylistResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    owner_id: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class PlaylistTrackResponse(BaseModel):
    id: str
    spotify_track_id: str
    added_by_id: str
    added_at: datetime

    class Config:
        from_attributes = True


class PlaylistDetailResponse(PlaylistResponse):
    tracks: list[PlaylistTrackResponse]


class HealthResponse(BaseModel):
    status: str
    message: str
    database: str
