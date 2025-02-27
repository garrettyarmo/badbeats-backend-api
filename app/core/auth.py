"""
@file: auth.py
@description:
This module implements authentication and authorization for the BadBeats API
using OAuth2 with JWT tokens. It provides functions for:
- Verifying passwords
- Creating and validating JWT tokens
- Getting the current authenticated user
- Defining OAuth2 password bearer scheme

@dependencies:
- passlib.context: For password hashing and verification
- jose: For JWT token encoding/decoding
- datetime: For token expiration management
- fastapi.security: For OAuth2 implementation
- pydantic: For data validation
- app.core.config: For configuration settings
- app.core.logger: For component-specific logging

@notes:
- Passwords are hashed using bcrypt algorithm
- JWT tokens include user ID, optional scopes, and expiration time
- Token expiration time is configurable via settings
- Error handling is implemented for credential verification and token validation
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.logger import setup_logger

# Create a component-specific logger
logger = setup_logger("app.core.auth")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 token URL (the login endpoint)
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scopes={
        "predictions": "Read predictions",
        "admin": "Full administrative access"
    }
)


class Token(BaseModel):
    """Schema for the token response."""
    access_token: str
    token_type: str = "bearer"
    expires_at: int  # Unix timestamp for token expiration


class TokenData(BaseModel):
    """Schema for data encoded in the JWT token."""
    user_id: Optional[str] = None
    scopes: List[str] = []


class User(BaseModel):
    """Basic user schema with authentication fields."""
    id: str
    email: str
    is_active: bool = True
    is_admin: bool = False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hashed version.
    
    Args:
        plain_password: The password in plain text
        hashed_password: The hashed password to verify against
        
    Returns:
        bool: True if the password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token with the provided data and expiration.
    
    Args:
        data: Dictionary of data to encode in the token
        expires_delta: Optional expiration time delta, defaults to settings value
        
    Returns:
        str: The encoded JWT token
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + settings.ACCESS_TOKEN_EXPIRE_DELTA
    
    # Add expiration claim
    to_encode.update({"exp": expire})
    
    # Create and return the encoded token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    logger.debug(f"Created access token for user_id: {data.get('sub')}")
    return encoded_jwt


async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme)
) -> User:
    """
    Get the current user from a JWT token.
    
    This function is used as a dependency in protected routes.
    
    Args:
        security_scopes: Security scopes required for the endpoint
        token: The JWT token to decode
        
    Returns:
        User: The authenticated user
        
    Raises:
        HTTPException: If authentication fails or user lacks required scopes
    """
    # Set authenticate value for WWW-Authenticate header
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    
    # Define the credentials exception for authentication failures
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    try:
        # Decode the JWT token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Extract user_id from token
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("Token is missing user_id (sub claim)")
            raise credentials_exception
        
        # Extract scopes from token
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(user_id=user_id, scopes=token_scopes)
            
    except (JWTError, ValidationError) as e:
        logger.warning(f"Token validation failed: {str(e)}")
        raise credentials_exception
    
    # Check if user exists (in a real app, this would query the database)
    # For the current MVP implementation, we'll create a mock user
    # In a real app, you would fetch the user from the database
    user = User(
        id=token_data.user_id,
        email=f"{token_data.user_id}@example.com",
        is_active=True,
        is_admin="admin" in token_data.scopes
    )
    
    # Verify that user has required scopes
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            logger.warning(f"User {user_id} does not have required scope: {scope}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify that the current user is active.
    
    This function is used as a dependency in routes that require an active user.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        User: The active user
        
    Raises:
        HTTPException: If the user is inactive
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.id}")
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user