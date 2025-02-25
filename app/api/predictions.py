"""
@file: predictions.py
@description:
Provides API endpoints to manage and retrieve sports betting predictions.
These endpoints now rely on the Supabase-based prediction_service module
for all database interactions.

Routes:
- GET /api/v1/predictions : fetch a list of all predictions
- POST /api/v1/predictions : create a new prediction

@dependencies:
- FastAPI APIRouter for route definitions.
- prediction_service for CRUD operations with Supabase.
- Pydantic schemas (PredictionCreate, PredictionOut, PredictionsResponse) 
  for validation and serialization.

@assumptions:
- The 'predictions' table exists in Supabase and matches the data schema.
- Future steps will handle authentication, error handling, rate-limiting, etc.
- Additional business logic (e.g., model-based picks or scheduling) is handled
  in other modules, integrated at later steps.
"""

from fastapi import APIRouter, HTTPException, status
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
from supabase import SupabaseException

router = APIRouter()


@router.get("/predictions", response_model=PredictionsResponse, tags=["Predictions"])
def get_predictions() -> PredictionsResponse:
    """
    GET /api/v1/predictions

    Retrieves a list of all predictions from the Supabase database.

    Returns:
        PredictionsResponse: An object containing a list of all predictions
        under a "picks" key. Each item conforms to the PredictionOut schema.

    Raises:
        HTTPException(500): If there's an error querying the database.
    
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
        predictions_list = get_all_predictions()
        return PredictionsResponse(picks=predictions_list)
    except SupabaseException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/predictions", response_model=PredictionOut, status_code=status.HTTP_201_CREATED, tags=["Predictions"])
def create_new_prediction(prediction_in: PredictionCreate) -> PredictionOut:
    """
    POST /api/v1/predictions

    Creates a new prediction record in the Supabase database.

    Args:
        prediction_in (PredictionCreate): 
            The required fields to create a new prediction.

    Returns:
        PredictionOut: The newly created prediction record.

    Raises:
        HTTPException(500): If there's an error saving to the database.

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
        new_pred = create_prediction(prediction_in)
        return new_pred
    except SupabaseException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
