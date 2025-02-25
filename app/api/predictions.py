"""
@file: predictions.py
@description:
Provides API endpoints to manage and retrieve sports betting predictions.

This module defines routes under the `/api/v1/predictions` path:
- GET to fetch a list of all predictions
- POST to create a new prediction

Note:
- Database actions are performed inline in this step. A dedicated service
  layer (prediction_service) will be implemented in Step 7.
- Authentication will be integrated in a future step (Step 11).
- Rate limiting, CORS enhancements, and HTTPS are future concerns.

@dependencies:
- FastAPI APIRouter for route definitions.
- SQLAlchemy session for database operations.
- Pydantic schemas (PredictionCreate, PredictionsResponse) for validation.

@assumptions:
- The `Prediction` model is already defined in `app.db.models`.
- The synchronous `Session` dependency (get_db) is used.
- Future steps will integrate advanced error handling, authentication,
  and separate business logic modules (services).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.db.models import Prediction
from app.schemas.predictions import (
    PredictionCreate,
    PredictionOut,
    PredictionsResponse
)

router = APIRouter()


@router.get("/predictions", response_model=PredictionsResponse, tags=["Predictions"])
def get_predictions(db: Session = Depends(get_db)) -> PredictionsResponse:
    """
    GET /api/v1/predictions

    Retrieves a list of all predictions from the database.

    Returns:
        PredictionsResponse: An object containing a list of all predictions
        under a "picks" key. Each item conforms to the PredictionOut schema.

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
        }
      ]
    }
    """
    predictions = db.query(Prediction).all()

    # Convert ORM objects to Pydantic models
    response_data: List[PredictionOut] = []
    for pred in predictions:
        response_data.append(
            PredictionOut(
                agent_id=pred.agent_id,
                game_id=pred.game_id,
                pick=pred.pick,
                logic=pred.logic,
                confidence=pred.confidence,
                result=pred.result
            )
        )

    return PredictionsResponse(picks=response_data)


@router.post("/predictions", response_model=PredictionOut, status_code=status.HTTP_201_CREATED, tags=["Predictions"])
def create_prediction(
    prediction_in: PredictionCreate,
    db: Session = Depends(get_db)
) -> PredictionOut:
    """
    POST /api/v1/predictions

    Creates a new prediction record in the database.

    Args:
        prediction_in (PredictionCreate): The required fields to create a new prediction.

    Returns:
        PredictionOut: The newly created prediction record.

    Raises:
        HTTPException(400): If a validation or logical constraint fails in future expansions.

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
    # Create new Prediction object from the incoming Pydantic model
    new_prediction = Prediction(
        agent_id=prediction_in.agent_id,
        game_id=prediction_in.game_id,
        pick=prediction_in.pick,
        logic=prediction_in.logic,
        confidence=prediction_in.confidence,
        result=prediction_in.result
    )

    # Persist to DB
    db.add(new_prediction)
    db.commit()
    db.refresh(new_prediction)

    # Return the newly created record in the schema format
    return PredictionOut(
        agent_id=new_prediction.agent_id,
        game_id=new_prediction.game_id,
        pick=new_prediction.pick,
        logic=new_prediction.logic,
        confidence=new_prediction.confidence,
        result=new_prediction.result
    )
