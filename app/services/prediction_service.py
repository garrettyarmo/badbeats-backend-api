"""/**
 * @file: prediction_service.py
 * @description 
 * This module provides service-level functions for managing betting predictions
 * and historical game data in the Supabase database. It handles CRUD operations
 * for predictions and storage/retrieval of NBA game data.
 * 
 * Key features:
 * - Prediction Management: Create and retrieve predictions.
 * - Historical Data: Store and fetch game data for efficient predictions.
 * 
 * @dependencies
 * - supabase: For database interactions.
 * - app.schemas.predictions: For prediction validation.
 * - uuid: For generating unique IDs.
 * - typing: For type annotations.
 * - app.core.logger: For logging.
 * 
 * @notes
 * - Assumes Supabase tables 'predictions' and 'games' exist.
 * - 'games' table stores historical data with fields: id, game_data, created_at, updated_at.
 * - Error handling is basic; enhance with retries for production.
 */"""

from datetime import datetime
import uuid
from typing import List, Dict, Any
import pytz
from supabase import SupabaseException

from app.db.supabase_client import supabase
from app.schemas.predictions import PredictionCreate, PredictionOut
from app.core.logger import setup_logger

# Initialize logger
logger = setup_logger("app.services.prediction_service")

def create_prediction(prediction_in: PredictionCreate) -> PredictionOut:
    """
    Create a new prediction in the 'predictions' table.

    Args:
        prediction_in: Prediction data to create.

    Returns:
        PredictionOut: Created prediction object.

    Raises:
        SupabaseException: If insertion fails.
    """
    record_id = str(uuid.uuid4())
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
        logger.info(f"Creating prediction for game {prediction_in.game_id}")
        response = supabase.table("predictions").insert(record_data).execute()
        if not response.data:
            error_msg = response.error or "Unknown error during insertion"
            logger.error(f"Supabase insertion error: {error_msg}")
            raise SupabaseException(error_msg)

        inserted_row = response.data[0]
        logger.debug(f"Inserted prediction with ID: {record_id}")
        return PredictionOut(
            agent_id=inserted_row["agent_id"],
            game_id=inserted_row["game_id"],
            pick=inserted_row["pick"],
            logic=inserted_row["logic"],
            confidence=inserted_row["confidence"],
            result=inserted_row["result"],
        )
    except Exception as e:
        logger.error(f"Failed to create prediction: {str(e)}")
        raise SupabaseException(f"Failed to create prediction: {str(e)}")

def get_all_predictions() -> List[PredictionOut]:
    """
    Retrieve all predictions from the 'predictions' table.

    Returns:
        List[PredictionOut]: List of predictions.

    Raises:
        SupabaseException: If retrieval fails.
    """
    try:
        logger.info("Retrieving all predictions")
        response = supabase.table("predictions").select("*").execute()
        if not response.data:
            error_msg = response.error or "Unknown error during retrieval"
            logger.error(f"Supabase retrieval error: {error_msg}")
            raise SupabaseException(error_msg)

        rows = response.data
        logger.debug(f"Retrieved {len(rows)} predictions")
        return [
            PredictionOut(
                agent_id=row["agent_id"],
                game_id=row["game_id"],
                pick=row["pick"],
                logic=row["logic"],
                confidence=row["confidence"],
                result=row["result"],
            ) for row in rows
        ]
    except Exception as e:
        logger.error(f"Failed to retrieve predictions: {str(e)}")
        raise SupabaseException(f"Failed to retrieve predictions: {str(e)}")

def store_historical_game_data(game_data: Dict[str, Any]) -> None:
    """
    Store or update historical game data in the 'games' table.

    Args:
        game_data: Game data dictionary from Ball Don't Lie API.
    """
    try:
        game_id = game_data.get("id")
        if not game_id:
            logger.warning("Game data missing ID, skipping storage")
            return

        record_data = {
            "id": str(game_id),
            "game_data": game_data,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # Upsert to avoid duplicates
        response = supabase.table("games").upsert(record_data, on_conflict="id").execute()
        if not response.data:
            error_msg = response.error or "Unknown error during game storage"
            logger.error(f"Supabase error storing game {game_id}: {error_msg}")
        else:
            logger.debug(f"Stored/updated game {game_id}")
    except Exception as e:
        logger.error(f"Failed to store game data: {str(e)}")

def get_stored_upcoming_games() -> List[Dict[str, Any]]:
    """
    Retrieve upcoming games from the 'games' table.

    Returns:
        List[Dict[str, Any]]: List of stored game data dictionaries.
    """
    try:
        logger.info("Retrieving stored upcoming games")
        now = datetime.now(pytz.UTC).isoformat()
        response = supabase.table("games").select("game_data").gt("game_data.date", now).execute()
        if not response.data:
            error_msg = response.error or "Unknown error during retrieval"
            logger.error(f"Supabase retrieval error: {error_msg}")
            return []

        games = [row["game_data"] for row in response.data]
        logger.debug(f"Retrieved {len(games)} upcoming games")
        return games
    except Exception as e:
        logger.error(f"Failed to retrieve upcoming games: {str(e)}")
        return []