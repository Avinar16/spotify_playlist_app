"""Authentication use cases - pure Python business logic"""
from uuid import uuid4
from app.core.auth import hash_password, verify_password, create_access_token, create_refresh_token, verify_token
from app.core.exceptions import AuthenticationError, ValidationError


class RegisterUserUseCase:
    """Register a new user"""
    
    def __init__(self, user_repository):
        self.user_repository = user_repository
    
    async def execute(self, email: str, username: str, password: str) -> dict:
        """Register a new user"""
        # Validate input
        if not email or not username or not password:
            raise ValidationError("Email, username, and password are required")
        
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")
        
        # Check if user exists
        existing_user = await self.user_repository.get_by_email(email)
        if existing_user:
            raise ValidationError("Email already registered")
        
        existing_username = await self.user_repository.get_by_username(username)
        if existing_username:
            raise ValidationError("Username already taken")
        
        # Create user
        user_id = str(uuid4())
        password_hash = hash_password(password)
        
        user = await self.user_repository.create(
            id=user_id,
            email=email,
            username=username,
            password_hash=password_hash
        )
        
        # Generate tokens
        access_token = create_access_token(user_id)
        refresh_token = create_refresh_token(user_id)
        
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "created_at": user.created_at,
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
        }


class LoginUserUseCase:
    """Authenticate user and return tokens"""
    
    def __init__(self, user_repository):
        self.user_repository = user_repository
    
    async def execute(self, email: str, password: str) -> dict:
        """Login user and return tokens"""
        # Find user by email
        user = await self.user_repository.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")
        
        # Verify password
        if not user.password_hash or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        
        # Generate tokens
        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)
        
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "created_at": user.created_at,
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
        }


class RefreshTokenUseCase:
    """Refresh access token using refresh token"""
    
    def __init__(self, user_repository):
        self.user_repository = user_repository
    
    async def execute(self, refresh_token: str) -> dict:
        """Validate refresh token and return new access token"""
        # Verify refresh token
        user_id = verify_token(refresh_token)
        if not user_id:
            raise AuthenticationError("Invalid or expired refresh token")
        
        # Get user
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        # Create new access token
        access_token = create_access_token(user_id)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }


class GetCurrentUserUseCase:
    """Get current user from user_id"""
    
    def __init__(self, user_repository):
        self.user_repository = user_repository
    
    async def execute(self, user_id: str) -> dict:
        """Get current user"""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "created_at": user.created_at,
            "spotify_id": user.spotify_id,
        }
