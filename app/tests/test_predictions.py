"""
@file: test_predictions.py
@description:
This module contains unit tests for the predictions functionality including:
- API endpoints testing through the FastAPI TestClient
- Service-level testing for prediction CRUD operations
- Validation of request/response schemas

The tests ensure that prediction endpoints and underlying services
work correctly for both authenticated and unauthenticated scenarios.

@dependencies:
- pytest: Testing framework
- fastapi.testclient: For testing FastAPI endpoints
- app.main: The main FastAPI application
- app.api.predictions: Prediction API routes
- app.services.prediction_service: Prediction service functions
- app.schemas.predictions: Pydantic schemas
- app.api.auth: Authentication utilities for testing

@notes:
- Tests are designed to be run independently
- Mock data and authentication are used to avoid external dependencies
- Success and failure scenarios are tested for comprehensive coverage
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from unittest import mock

from app.main import app
from app.schemas.predictions import PredictionCreate, PredictionOut
from app.services.prediction_service import create_prediction, get_all_predictions
from app.api.auth import create_access_token

# Create test client
client = TestClient(app)


def test_create_prediction_service():
    """
    Test creating a prediction through the service layer.
    This tests the create_prediction function directly.
    """
    # Mock the Supabase response
    with mock.patch('app.services.prediction_service.supabase') as mock_supabase:
        # Setup the mock to return a successful response
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock.MagicMock(
            data=[{
                "agent_id": "test-agent",
                "game_id": 12345,
                "pick": "Lakers -4",
                "logic": "Test logic",
                "confidence": 0.8,
                "result": "pending"
            }],
            error=None
        )
        
        # Create test prediction data
        prediction_in = PredictionCreate(
            agent_id="test-agent",
            game_id=12345,
            pick="Lakers -4",
            logic="Test logic",
            confidence=0.8,
            result="pending"
        )
        
        # Call the service function
        result = create_prediction(prediction_in)
        
        # Verify the result
        assert result.agent_id == "test-agent"
        assert result.game_id == 12345
        assert result.pick == "Lakers -4"
        assert result.logic == "Test logic"
        assert result.confidence == 0.8
        assert result.result == "pending"
        
        # Verify the mock was called correctly
        mock_supabase.table.assert_called_once_with("predictions")
        mock_supabase.table().insert.assert_called_once()


def test_get_all_predictions_service():
    """
    Test retrieving all predictions through the service layer.
    This tests the get_all_predictions function directly.
    """
    # Mock the Supabase response
    with mock.patch('app.services.prediction_service.supabase') as mock_supabase:
        # Setup the mock to return a list of predictions
        mock_supabase.table.return_value.select.return_value.execute.return_value = mock.MagicMock(
            data=[
                {
                    "agent_id": "test-agent-1",
                    "game_id": 12345,
                    "pick": "Lakers -4",
                    "logic": "Test logic 1",
                    "confidence": 0.8,
                    "result": "pending"
                },
                {
                    "agent_id": "test-agent-2",
                    "game_id": 12346,
                    "pick": "Warriors +2",
                    "logic": "Test logic 2",
                    "confidence": 0.9,
                    "result": "pending"
                }
            ],
            error=None
        )
        
        # Call the service function
        results = get_all_predictions()
        
        # Verify the results
        assert len(results) == 2
        assert results[0].agent_id == "test-agent-1"
        assert results[0].game_id == 12345
        assert results[1].agent_id == "test-agent-2"
        assert results[1].game_id == 12346
        
        # Verify the mock was called correctly
        mock_supabase.table.assert_called_once_with("predictions")
        mock_supabase.table().select.assert_called_once_with("*")


def test_get_predictions_endpoint_unauthorized():
    """
    Test that the predictions API endpoint returns 401 Unauthorized
    when called without authentication.
    """
    response = client.get("/api/v1/predictions")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_get_predictions_endpoint_authorized():
    """
    Test that the predictions API endpoint returns predictions successfully
    when called with valid authentication.
    """
    # Mock the get_all_predictions function
    with mock.patch('app.api.predictions.get_all_predictions') as mock_get_predictions:
        # Setup the mock to return a list of predictions
        mock_get_predictions.return_value = [
            PredictionOut(
                agent_id="test-agent-1",
                game_id=12345,
                pick="Lakers -4",
                logic="Test logic 1",
                confidence=0.8,
                result="pending"
            )
        ]
        
        # Create a valid token for testing
        token = create_access_token(
            data={"sub": "user", "scopes": ["predictions"]},
            expires_delta=None
        )
        
        # Call the endpoint with authorization
        response = client.get(
            "/api/v1/predictions",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        assert "picks" in data
        assert len(data["picks"]) == 1
        assert data["picks"][0]["agent_id"] == "test-agent-1"
        assert data["picks"][0]["game_id"] == 12345
        
        # Verify the mock was called
        mock_get_predictions.assert_called_once()


def test_create_prediction_endpoint_authorized():
    """
    Test that the create prediction API endpoint creates a prediction successfully
    when called with valid authentication.
    """
    # Mock the create_prediction function
    with mock.patch('app.api.predictions.create_prediction') as mock_create_prediction:
        # Setup the mock to return a created prediction
        mock_create_prediction.return_value = PredictionOut(
            agent_id="test-agent",
            game_id=12345,
            pick="Lakers -4",
            logic="Test logic",
            confidence=0.8,
            result="pending"
        )
        
        # Create a valid token for testing
        token = create_access_token(
            data={"sub": "user", "scopes": ["predictions"]},
            expires_delta=None
        )
        
        # Create test prediction data
        prediction_data = {
            "agent_id": "test-agent",
            "game_id": 12345,
            "pick": "Lakers -4",
            "logic": "Test logic",
            "confidence": 0.8,
            "result": "pending"
        }
        
        # Call the endpoint with authorization
        response = client.post(
            "/api/v1/predictions",
            headers={"Authorization": f"Bearer {token}"},
            json=prediction_data
        )
        
        # Verify the response
        assert response.status_code == 201
        data = response.json()
        assert data["agent_id"] == "test-agent"
        assert data["game_id"] == 12345
        assert data["pick"] == "Lakers -4"
        
        # Verify the mock was called with correct data
        mock_create_prediction.assert_called_once()
        called_arg = mock_create_prediction.call_args[0][0]
        assert called_arg.agent_id == "test-agent"
        assert called_arg.game_id == 12345
        assert called_arg.pick == "Lakers -4"


def test_create_prediction_invalid_data():
    """
    Test that the create prediction API endpoint validates input data properly.
    """
    # Create a valid token for testing
    token = create_access_token(
        data={"sub": "user", "scopes": ["predictions"]},
        expires_delta=None
    )
    
    # Test with missing required fields
    invalid_data = {
        "agent_id": "test-agent",
        # Missing game_id
        "pick": "Lakers -4",
        "logic": "Test logic",
        "confidence": 0.8,
        "result": "pending"
    }
    
    response = client.post(
        "/api/v1/predictions",
        headers={"Authorization": f"Bearer {token}"},
        json=invalid_data
    )
    
    # Verify validation error
    assert response.status_code == 422
    
    # Test with invalid confidence value (outside range 0-1)
    invalid_data = {
        "agent_id": "test-agent",
        "game_id": 12345,
        "pick": "Lakers -4",
        "logic": "Test logic",
        "confidence": 1.5,  # Invalid: > 1.0
        "result": "pending"
    }
    
    response = client.post(
        "/api/v1/predictions",
        headers={"Authorization": f"Bearer {token}"},
        json=invalid_data
    )
    
    # Verify validation error
    assert response.status_code == 422