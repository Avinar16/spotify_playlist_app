"""User repository - data access layer"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database.models import UserModel


class UserRepository:
    """Repository for user database operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, id: str, email: str, username: str, password_hash: str = None) -> UserModel:
        """Create a new user"""
        user = UserModel(
            id=id,
            email=email,
            username=username,
            password_hash=password_hash,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def get_by_id(self, user_id: str) -> UserModel:
        """Get user by ID"""
        result = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> UserModel:
        """Get user by email"""
        result = await self.db.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> UserModel:
        """Get user by username"""
        result = await self.db.execute(
            select(UserModel).where(UserModel.username == username)
        )
        return result.scalar_one_or_none()
    
    async def update_spotify_tokens(
        self,
        user_id: str,
        spotify_id: str,
        access_token: str,
        refresh_token: str = None,
    ) -> UserModel:
        """Update user's Spotify tokens"""
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        user.spotify_id = spotify_id
        user.access_token = access_token
        user.refresh_token = refresh_token
        
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def clear_spotify_tokens(self, user_id: str) -> UserModel:
        """Clear Spotify tokens for user"""
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        user.spotify_id = None
        user.access_token = None
        user.refresh_token = None
        
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def update(self, user: UserModel) -> UserModel:
        """Update user record"""
        await self.db.merge(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def update_favorite_genres(self, user_id: str, genres_json: str) -> UserModel:
        """Update user's favorite genres"""
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        user.favorite_genres = genres_json
        await self.db.commit()
        await self.db.refresh(user)
        return user
