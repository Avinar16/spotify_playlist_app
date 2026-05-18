"""Tests for auth use cases"""
import pytest
from uuid import uuid4
from app.use_cases.auth import RegisterUserUseCase, LoginUserUseCase
from app.infrastructure.database.user_repository import UserRepository
from app.core.exceptions import ValidationError, AuthenticationError
from app.infrastructure.database.models import UserModel


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_user_success(db_session):
    """Test successful user registration"""
    repo = UserRepository(db_session)
    use_case = RegisterUserUseCase(repo)
    
    result = await use_case.execute(
        email="test@example.com",
        username="testuser",
        password="password123"
    )
    
    assert result["user"]["id"]
    assert result["user"]["email"] == "test@example.com"
    assert result["user"]["username"] == "testuser"
    assert result["access_token"]
    assert result["refresh_token"]
    assert "password_hash" not in result["user"]  # Should not expose password hash


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_user_duplicate_email(db_session):
    """Test registration with duplicate email"""
    repo = UserRepository(db_session)
    use_case = RegisterUserUseCase(repo)
    
    # Register first user
    await use_case.execute(
        email="test@example.com",
        username="testuser1",
        password="password123"
    )
    
    # Try to register with same email
    with pytest.raises(ValidationError):
        await use_case.execute(
            email="test@example.com",
            username="testuser2",
            password="password123"
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_user_invalid_email(db_session):
    """Test registration with invalid email"""
    repo = UserRepository(db_session)
    use_case = RegisterUserUseCase(repo)
    
    with pytest.raises(ValidationError):
        await use_case.execute(
            email="invalid-email",
            username="testuser",
            password="password123"
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_user_success(db_session):
    """Test successful login"""
    repo = UserRepository(db_session)
    register_use_case = RegisterUserUseCase(repo)
    login_use_case = LoginUserUseCase(repo)
    
    # Register user
    await register_use_case.execute(
        email="test@example.com",
        username="testuser",
        password="password123"
    )
    
    # Login
    result = await login_use_case.execute(
        email="test@example.com",
        password="password123"
    )
    
    assert result["user"]["id"]
    assert result["user"]["email"] == "test@example.com"
    assert result["user"]["username"] == "testuser"
    assert result["access_token"]
    assert result["refresh_token"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_user_wrong_password(db_session):
    """Test login with wrong password"""
    repo = UserRepository(db_session)
    register_use_case = RegisterUserUseCase(repo)
    login_use_case = LoginUserUseCase(repo)
    
    # Register user
    await register_use_case.execute(
        email="test@example.com",
        username="testuser",
        password="password123"
    )
    
    # Try to login with wrong password
    with pytest.raises(AuthenticationError):
        await login_use_case.execute(
            email="test@example.com",
            password="wrongpassword"
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_login_user_not_found(db_session):
    """Test login with non-existent user"""
    repo = UserRepository(db_session)
    login_use_case = LoginUserUseCase(repo)
    
    with pytest.raises(AuthenticationError):
        await login_use_case.execute(
            email="nonexistent@example.com",
            password="password123"
        )
