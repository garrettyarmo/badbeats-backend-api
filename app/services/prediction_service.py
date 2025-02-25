"""
@file: prediction_service.py
@description:
This module contains service-level functions for creating, retrieving, 
and managing betting predictions in the Supabase database.

@dependencies:
- supabase: For interacting with the Supabase backend. 
- pydantic schemas (PredictionCreate, PredictionOut) for validation.
- python's uuid library for generating UUIDs.
- typing library for type annotations.

@notes:
- We store predictions in a Supabase table named "predictions".
- Each record includes agent_id, game_id, pick, logic, confidence, 
  and result, along with a generated UUID primary key.
- Because the project specification does not require returning the 'id',
  we omit it from our Pydantic response model. The table can still store it.
- created_at and updated_at can be automatically managed by Supabase 
  using 'created_at' and 'updated_at' columns if you configure them in
  your Supabase table with default/current_timestamp. 
  We do not expose them in the API responses based on the specification.

@limitations:
- Basic error handling is included. For production, consider more
  robust logging and retry logic.
- Ensure the "predictions" table exists in Supabase with the relevant columns:
    id (uuid), agent_id (int), game_id (int), pick (text),
    logic (text), confidence (float), result (text), created_at (timestamp), 
    updated_at (timestamp).
"""

import uuid
from typing import List
from supabase import SupabaseException

from app.db.supabase_client import supabase
from app.schemas.predictions import PredictionCreate, PredictionOut

def create_prediction(prediction_in: PredictionCreate) -> PredictionOut:
    """
    Create a new prediction in the Supabase 'predictions' table.

    Args:
        prediction_in (PredictionCreate): The Pydantic model containing required fields.
    
    Returns:
        PredictionOut: The newly created prediction data, matching the project's response spec.
    
    Raises:
        SupabaseException: If the insertion fails due to connectivity or other issues.
    """
    # Generate a UUID for the record's primary key
    record_id = str(uuid.uuid4())
    
    # Prepare the record data
    record_data = {
        "id": record_id,
        "agent_id": prediction_in.agent_id,
        "game_id": prediction_in.game_id,
        "pick": prediction_in.pick,
        "logic": prediction_in.logic,
        "confidence": prediction_in.confidence,
        "result": prediction_in.result,
    }

    try:
        # Insert into Supabase
        response = supabase.table("predictions").insert(record_data).execute()
        if response.data is None:
            # If Supabase didn't return data, raise an error
            raise SupabaseException(response.error or "Unknown error during insertion.")
        
        # We'll take the inserted row from Supabase
        inserted_row = response.data[0]
        
        # Build a PredictionOut object from the row data
        created_prediction = PredictionOut(
            agent_id=inserted_row["agent_id"],
            game_id=inserted_row["game_id"],
            pick=inserted_row["pick"],
            logic=inserted_row["logic"],
            confidence=inserted_row["confidence"],
            result=inserted_row["result"],
        )
        return created_prediction
    
    except Exception as e:
        # Catch any errors from supabase or Python
        raise SupabaseException(f"Failed to create prediction: {str(e)}")


def get_all_predictions() -> List[PredictionOut]:
    """
    Retrieve all predictions from the Supabase 'predictions' table.

    Returns:
        List[PredictionOut]: A list of PredictionOut objects matching
        the project's response specification.
    
    Raises:
        SupabaseException: If retrieval fails.
    """
    try:
        response = supabase.table("predictions").select("*").execute()
        if response.data is None:
            # If Supabase didn't return data, raise an error
            raise SupabaseException(response.error or "Unknown error during retrieval.")
        
        rows = response.data
        # Convert each row into a PredictionOut model 
        predictions_out = []
        for row in rows:
            predictions_out.append(
                PredictionOut(
                    agent_id=row["agent_id"],
                    game_id=row["game_id"],
                    pick=row["pick"],
                    logic=row["logic"],
                    confidence=row["confidence"],
                    result=row["result"],
                )
            )
        return predictions_out
    except Exception as e:
        raise SupabaseException(f"Failed to retrieve predictions: {str(e)}")
