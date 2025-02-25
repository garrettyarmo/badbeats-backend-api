"""
Database Session Management Module.

This module handles the creation and management of database connections and sessions
using SQLAlchemy. It provides utilities for connecting to the PostgreSQL database,
creating sessions, and managing database transactions.

Key features:
- Database engine configuration
- Session maker setup
- FastAPI dependency for session injection
- Async support for optimal FastAPI performance

Usage:
- In FastAPI route handlers, use the get_db dependency to obtain a database session
- Example: `def my_route(db: Session = Depends(get_db)):`
"""

import os
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi import Depends

# Import environment variables
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

# For synchronous operations
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Check connection before using it
    pool_size=10,        # Adjust pool size for Supabase
    max_overflow=20,     # Allow additional connections when needed
    pool_recycle=300,    # Recycle connections every 5 minutes
    echo=os.getenv("APP_ENV") == "development",  # Log SQL in development mode
)

# Create a sessionmaker for creating database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Convert PostgreSQL URL to AsyncPG URL if needed
# This handles the case where DATABASE_URL is in standard format
async_database_url = DATABASE_URL
if async_database_url.startswith("postgresql://"):
    async_database_url = async_database_url.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine for async operations
async_engine = create_async_engine(
    async_database_url,
    echo=os.getenv("APP_ENV") == "development",
    pool_pre_ping=True,
)

# Create async session maker
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Dependency for synchronous database operations
def get_db():
    """
    FastAPI dependency that provides a database session.
    
    This function creates a new SQLAlchemy session and ensures it is properly
    closed after use, even if exceptions occur during the request handling.
    
    Yields:
        Session: A SQLAlchemy database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency for asynchronous database operations
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an asynchronous database session.
    
    This function creates a new SQLAlchemy async session and ensures it is properly
    closed after use, even if exceptions occur during the request handling.
    
    Yields:
        AsyncSession: A SQLAlchemy async database session.
    """
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()