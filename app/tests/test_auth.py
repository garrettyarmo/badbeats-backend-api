"""
@file: test_auth.py
@description:
Test suite for authentication functionality in the BadBeats API.
Tests include authentication flow, token validation, and protected endpoint access.

@dependencies:
- pytest: For test framework
- fastapi.testclient: For testing FastAPI applications
- app.main: The main FastAPI application
- app.core.auth: Authentication utilities

@notes:
- Tests use the test client to simulate HTTP requests
- Mock users from the auth module are used for authentication
- Both success and failure scenarios are tested
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.auth import MOCK_USERS

# Create test client
client = TestClient(app)


def test_login_success():
    """Test successful login and token retrieval."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "user",
            "password": "userpassword"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_at" in data


def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "user",
            "password": "wrongpassword"
        }
    )
    
    assert response.status_code == 401
    assert "detail" in response.json()


def test_register_user():
    """Test user registration."""
    response = client.post(
        "/api/v1/auth/register",
        params={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword"
        }
    )
    
    assert response.status_code == 201
    assert response.json()["status"] == "success"
    
    # Verify user can now login
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_register_duplicate_user():
    """Test registering a user with an existing username."""
    # First registration should succeed
    response = client.post(
        "/api/v1/auth/register",
        params={
            "username": "duplicateuser",
            "email": "duplicate@example.com",
            "password": "password123"
        }
    )
    assert response.status_code == 201
    
    # Second registration with same username should fail
    response = client.post(
        "/api/v1/auth/register",
        params={
            "username": "duplicateuser",
            "email": "another@example.com",
            "password": "password456"
        }
    )
    assert response.status_code == 400
    assert "detail" in response.json()


def test_protected_endpoint_without_token():
    """Test accessing a protected endpoint without a token."""
    response = client.get("/api/v1/predictions")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_protected_endpoint_with_token():
    """Test accessing a protected endpoint with a valid token."""
    # First login to get token
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": "user",
            "password": "userpassword"
        }
    )
    token = login_response.json()["access_token"]
    
    # Now access protected endpoint with token
    response = client.get(
        "/api/v1/predictions",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert "picks" in response.json()