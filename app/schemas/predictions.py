"""
@file: predictions.py
@description:
Pydantic schemas for request validation and response serialization
of sports betting predictions.

Schemas:
- PredictionBase: Base fields shared among request/response
- PredictionCreate: Fields required to create a new prediction
- PredictionOut: Fields exposed in API responses for a single prediction
- PredictionsResponse: Wrapper schema for returning multiple predictions

@notes:
- In the project request example, the API returns:
  {
    "picks": [
      {
        "agent_id": 1,
        "game_id": 12345,
        "pick": "Lakers -4",
        "logic": "some logic text",
        "confidence": 0.8,
        "result": "pending"
      }
    ]
  }
  This is mirrored by the PredictionsResponse schema.
- Result defaults to "pending" in DB, but can be overridden if needed.
- Additional fields (e.g. created_at, updated_at) are stored in the DB model
  but not returned here to match the project specification.

@dependencies:
- pydantic: for data validation and serialization
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class PredictionBase(BaseModel):
    """
    Shared fields between request and response models.
    """
    agent_id: str = Field(..., description="Identifies the model/agent making the prediction.")
    game_id: int = Field(..., description="Unique identifier for the game.")
    pick: str = Field(..., description="Team and spread, e.g. 'Lakers -4'.")
    logic: str = Field(..., description="A paragraph explaining the reasoning for this pick.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score from 0 to 1.")
    result: str = Field("pending", description="Outcome of the pick, e.g. 'pending', 'win', or 'loss'.")


class PredictionCreate(PredictionBase):
    """
    Fields required for creating a new prediction record.
    This matches the database fields except for the ID, 
    which is generated automatically in the DB.
    """
    pass


class PredictionOut(PredictionBase):
    """
    Fields returned by the API for a single prediction record.
    In this basic example, we omit the database-generated `id`,
    `created_at`, and `updated_at` fields to match the project spec.
    """
    pass


class PredictionsResponse(BaseModel):
    """
    Wrapper for returning multiple predictions 
    under a top-level "picks" key.
    """
    picks: List[PredictionOut]
