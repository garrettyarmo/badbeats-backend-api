"""
@file: auth.py
@description:
This module implements authentication endpoints for the BadBeats API,
including user login and registration routes. It uses the OAuth2 and JWT
implementation from core.auth to handle authentication flows.

Routes:
- POST /api/v1/auth/login: Authenticate a user and return an access token
- POST /api/v1/auth/register: Register a new user (placeholder for future implementation)

@dependencies:
- fastapi: For API routing
- fastapi.security: For OAuth2 password request form
- app.core.auth: For authentication utilities
- app.schemas: For request/response validation

@notes:
- The current implementation focuses on the login flow
- User management (registration, user storage) is minimal for the MVP
- In a production environment, this would connect to a user database
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth import (
    Token,
    User,
    create_access_token,
    get_password_hash,
    verify_password
)
from app.core.config import settings
from app.core.logger import setup_logger

# Create a component-specific logger
logger = setup_logger("app.api.auth")

# Create a router instance
router = APIRouter()

# Mock user database for demonstration
# In a real application, this would be stored in a database
MOCK_USERS = {
    "admin": {
        "id": "admin",
        "email": "admin@example.com",
        "hashed_password": get_password_hash("adminpassword"),
        "is_active": True,
        "is_admin": True
    },
    "user": {
        "id": "user",
        "email": "user@example.com",
        "hashed_password": get_password_hash("userpassword"),
        "is_active": True,
        "is_admin": False
    }
}


def get_user(username: str) -> User:
    """
    Get a user by username from the mock database.
    
    Args:
        username: The username to look up
        
    Returns:
        User: The user if found
        
    Raises:
        HTTPException: If user is not found
    """
    if username in MOCK_USERS:
        user_data = MOCK_USERS[username]
        return User(
            id=user_data["id"],
            email=user_data["email"],
            is_active=user_data["is_active"],
            is_admin=user_data["is_admin"]
        )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


def authenticate_user(username: str, password: str) -> User:
    """
    Authenticate a user with username and password.
    
    Args:
        username: The username to authenticate
        password: The password to verify
        
    Returns:
        User: The authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        user_dict = MOCK_USERS.get(username)
        if not user_dict:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not verify_password(password, user_dict["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return User(
            id=user_dict["id"],
            email=user_dict["email"],
            is_active=user_dict["is_active"],
            is_admin=user_dict["is_admin"]
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/login", response_model=Token, tags=["Authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Token:
    """
    Authenticate a user and return a JWT access token.
    
    This endpoint follows the OAuth2 password flow.
    
    Args:
        form_data: OAuth2 password request form containing username and password
        
    Returns:
        Token: JWT access token with expiration time
        
    Raises:
        HTTPException: If authentication fails
    """
    # Authenticate the user
    user = authenticate_user(form_data.username, form_data.password)
    
    # Define scopes based on user type
    scopes = ["predictions"]
    if user.is_admin:
        scopes.append("admin")
    
    # Create access token
    access_token_expires = settings.ACCESS_TOKEN_EXPIRE_DELTA
    
    # Current time plus expiration in seconds (for the client)
    expires_at = int((datetime.utcnow() + access_token_expires).timestamp())
    
    # Create the JWT token with user ID and scopes
    access_token = create_access_token(
        data={"sub": user.id, "scopes": scopes},
        expires_delta=access_token_expires
    )
    
    logger.info(f"User {user.id} logged in successfully")
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_at=expires_at
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, tags=["Authentication"])
async def register_user(
    username: str,
    email: str,
    password: str
) -> dict:
    """
    Register a new user.
    
    This is a placeholder endpoint for future implementation.
    In a real application, this would store the user in a database.
    
    Args:
        username: Desired username
        email: User's email address
        password: User's password
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If registration fails
    """
    # Check if user already exists
    if username in MOCK_USERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # This would normally save to a database
    # For the mock implementation, we'll just add to our in-memory dict
    MOCK_USERS[username] = {
        "id": username,
        "email": email,
        "hashed_password": get_password_hash(password),
        "is_active": True,
        "is_admin": False
    }
    
    logger.info(f"New user registered: {username}")
    
    return {
        "status": "success",
        "message": "User registered successfully"
    }