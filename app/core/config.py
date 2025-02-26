"""
@file: config.py
@description:
This module provides centralized configuration management for the BadBeats backend API.
It loads environment variables and provides typed access to configuration settings
used throughout the application.

The configuration includes settings for:
- Application general settings (debug mode, environment)
- Database connection
- Authentication (JWT)
- External APIs (BallDontLie, OpenAI)
- Celery and Redis for task scheduling
- Logging parameters

@dependencies:
- pydantic: For settings validation
- pydantic_settings: For environment variable loading
- dotenv: For loading environment variables from .env file

@notes:
- All sensitive configuration is loaded from environment variables
- Default values are provided where appropriate
- Settings are validated at startup time
- Different configurations can be loaded based on the APP_ENV variable
"""

import os
from typing import Optional, Dict, Any, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from datetime import timedelta

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Provides typed access to all configuration parameters used in the application.
    """
    # Application Settings
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    SECRET_KEY: str = Field(default="your_secret_key_here")
    
    # Database
    SUPABASE_URL: str = Field(default="https://your_supabase_project_id.supabase.co")
    SUPABASE_KEY: str = Field(default="your_supabase_key")
    
    # Authentication
    JWT_SECRET: str = Field(default="your_jwt_secret_here")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # External APIs
    BALL_DONT_LIE_API_KEY: Optional[str] = Field(default=None)
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    GROQ_API_KEY: Optional[str] = Field(default=None)
    
    # Redis and Celery
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @field_validator("CELERY_BROKER_URL", mode="before")
    def set_celery_broker_url(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        """
        Set the Celery broker URL to the Redis URL if not explicitly specified.
        """
        if v is not None:
            return v
        redis_url = values.data.get("REDIS_URL", "redis://localhost:6379/0")
        return redis_url
    
    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    def set_celery_result_backend(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        """
        Set the Celery result backend to the Redis URL if not explicitly specified.
        """
        if v is not None:
            return v
        redis_url = values.data.get("REDIS_URL", "redis://localhost:6379/0")
        return redis_url
    
    @property
    def ACCESS_TOKEN_EXPIRE_DELTA(self) -> timedelta:
        """
        Convert the access token expiration minutes to a timedelta object.
        """
        return timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)


# Create a global settings object
settings = Settings()

def get_settings() -> Settings:
    """
    Function to get the settings object for dependency injection in FastAPI.
    """
    return settings