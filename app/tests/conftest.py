"""
@file: conftest.py
@description:
This module provides pytest fixtures and configuration for the BadBeats API test suite.
It sets up common test fixtures that can be reused across test modules.

Fixtures include:
- Mock authentication tokens
- Mock database connections
- Test client setup
- Environment configuration for testing

@dependencies:
- pytest: For test framework and fixtures
- fastapi.testclient: For testing FastAPI applications
- app.main: The main FastAPI application
- app.core.auth: Authentication utilities

@notes:
- Fixtures are automatically available to all test modules in the package
- The module configures pytest for the specific needs of this application
- Environment variables are temporarily modified during tests
"""

import pytest
import os
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import create_access_token


@pytest.fixture
def test_client():
    """
    Fixture that returns a TestClient instance for the FastAPI app.
    This allows tests to make requests to the application.
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture
def user_token():
    """
    Fixture that returns a valid user JWT token for testing.
    This token has standard user permissions.
    """
    token = create_access_token(
        data={"sub": "user", "scopes": ["predictions"]},
        expires_delta=None
    )
    return token


@pytest.fixture
def admin_token():
    """
    Fixture that returns a valid admin JWT token for testing.
    This token has admin permissions.
    """
    token = create_access_token(
        data={"sub": "admin", "scopes": ["predictions", "admin"]},
        expires_delta=None
    )
    return token


@pytest.fixture(autouse=True)
def setup_test_environment():
    """
    Fixture that sets up the test environment.
    This fixture runs automatically for each test.
    """
    # Store original environment variables
    original_env = {}
    test_env = {
        "APP_ENV": "test",
        "TESTING": "True",
        "DATABASE_URL": "postgresql://postgres:password@localhost:5432/test_db",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_KEY": "test-key",
        "JWT_SECRET": "test-secret",
        "REDIS_URL": "redis://localhost:6379/1"
    }
    
    # Save original values and set test values
    for key, value in test_env.items():
        if key in os.environ:
            original_env[key] = os.environ[key]
        os.environ[key] = value
    
    # Run the test
    yield
    
    # Restore original environment variables
    for key in test_env:
        if key in original_env:
            os.environ[key] = original_env[key]
        else:
            del os.environ[key]