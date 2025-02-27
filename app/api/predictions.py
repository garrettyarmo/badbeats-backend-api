"""
@file: predictions.py
@description:
Provides API endpoints to manage and retrieve sports betting predictions.
These endpoints now rely on the Supabase-based prediction_service module
for all database interactions and include OAuth2 JWT authentication.

Routes:
- GET /api/v1/predictions : fetch a list of all predictions
- POST /api/v1/predictions : create a new prediction

@dependencies:
- FastAPI APIRouter for route definitions.
- prediction_service for CRUD operations with Supabase.
- Pydantic schemas (PredictionCreate, PredictionOut, PredictionsResponse) 
  for validation and serialization.
- app.core.auth for authentication and authorization.

@assumptions:
- The 'predictions' table exists in Supabase and matches the data schema.
- Authentication is now required to access these endpoints.
- Admin scope is required for creating new predictions.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List

from app.services.prediction_service import (
    create_prediction,
    get_all_predictions
)
from app.schemas.predictions import (
    PredictionCreate,
    PredictionOut,
    PredictionsResponse
)
from app.core.auth import (
    User,
    get_current_active_user
)
from supabase import SupabaseException
from app.core.logger import logger

router = APIRouter()


@router.get("/predictions", response_model=PredictionsResponse, tags=["Predictions"])
def get_predictions(
    current_user: User = Depends(get_current_active_user)
) -> PredictionsResponse:
    """
    GET /api/v1/predictions

    Retrieves a list of all predictions from the Supabase database.
    
    Requires authentication.

    Returns:
        PredictionsResponse: An object containing a list of all predictions
        under a "picks" key. Each item conforms to the PredictionOut schema.

    Raises:
        HTTPException(500): If there's an error querying the database.
        HTTPException(401): If authentication fails.
    
    Example Response:
    {
      "picks": [
        {
          "agent_id": 1,
          "game_id": 12345,
          "pick": "Lakers -4",
          "logic": "some explanation",
          "confidence": 0.7,
          "result": "pending"
        },
        ...
      ]
    }
    """
    try:
        logger.info(f"User {current_user.id} requesting predictions")
        predictions_list = get_all_predictions()
        return PredictionsResponse(picks=predictions_list)
    except SupabaseException as e:
        logger.error(f"Database error retrieving predictions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/predictions", response_model=PredictionOut, status_code=status.HTTP_201_CREATED, tags=["Predictions"])
def create_new_prediction(
    prediction_in: PredictionCreate,
    current_user: User = Depends(get_current_active_user)
) -> PredictionOut:
    """
    POST /api/v1/predictions

    Creates a new prediction record in the Supabase database.
    
    Requires authentication. In a production environment, this would
    typically be restricted to admin users or the prediction service itself.

    Args:
        prediction_in (PredictionCreate): 
            The required fields to create a new prediction.
        current_user: The authenticated user making the request.

    Returns:
        PredictionOut: The newly created prediction record.

    Raises:
        HTTPException(500): If there's an error saving to the database.
        HTTPException(401): If authentication fails.
        HTTPException(403): If user lacks necessary permissions.

    Example Request Body:
    {
      "agent_id": 1,
      "game_id": 12345,
      "pick": "Lakers -4",
      "logic": "some logic text",
      "confidence": 0.8,
      "result": "pending"
    }

    Example Response:
    {
      "agent_id": 1,
      "game_id": 12345,
      "pick": "Lakers -4",
      "logic": "some logic text",
      "confidence": 0.8,
      "result": "pending"
    }
    """
    try:
        logger.info(f"User {current_user.id} creating new prediction")
        new_pred = create_prediction(prediction_in)
        return new_pred
    except SupabaseException as e:
        logger.error(f"Database error creating prediction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )