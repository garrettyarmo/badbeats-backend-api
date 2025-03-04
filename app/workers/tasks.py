"""
/**
 * @file: tasks.py
 * @description 
 * This module contains utility functions for managing the predictions workflow in the BadBeats backend.
 * Previously a Celery task module, it has been refactored to remove Celery dependency, providing
 * synchronous functions for data ingestion, prediction scheduling, and generation. These functions
 * can be called directly or via a scheduled mechanism (e.g., cron).
 * 
 * Key features:
 * - Data Ingestion: Fetches and updates NBA game data daily.
 * - Prediction Generation: Generates predictions for upcoming games using stored data.
 * - Data Preparation: Prepares structured and unstructured data for predictions.
 * 
 * @dependencies
 * - asyncio: For asynchronous API calls.
 * - datetime: For time calculations.
 * - app.services.ball_dont_lie_api: For NBA data fetching.
 * - app.services.news_ingestion: For news and injury data.
 * - app.llm.prediction_model: For prediction generation (replaces LangChain).
 * - app.services.prediction_service: For storing predictions and data.
 * - app.schemas.predictions: For data validation.
 * - app.core.logger: For logging.
 * 
 * @notes
 * - Functions are synchronous wrappers around async operations for simplicity.
 * - Error handling logs issues and returns None or partial results to allow continuation.
 * - Assumes a daily run schedule; adjust for more frequent updates if needed.
 * - Historical data is stored via prediction_service.py, fetched once daily.
 */
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pytz

from app.services.ball_dont_lie_api import (
    get_upcoming_games,
    get_game_by_id,
    get_team_stats_averages
)
from app.services.news_ingestion import (
    get_recent_news_for_team,
    get_team_injury_report
)
from app.services.prediction_service import (
    create_prediction,
    store_historical_game_data,
    get_stored_upcoming_games
)
from app.llm.prediction_model import create_prediction_model, PredictionInput
from app.schemas.predictions import PredictionCreate
from app.core.logger import setup_logger

# Initialize logger
logger = setup_logger("app.workers.tasks")

def ingest_nba_data() -> Dict[str, Any]:
    """
    Ingest NBA data from external APIs and store it in Supabase.

    This function fetches upcoming games and stores them as historical data,
    intended to run daily to keep data fresh.

    Returns:
        Dict[str, Any]: Summary of ingested data with status and count.
    """
    logger.info("Starting NBA data ingestion")
    try:
        # Run async operations synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        upcoming_games = loop.run_until_complete(get_upcoming_games(days_ahead=7))
        loop.close()

        # Store games in Supabase
        for game in upcoming_games:
            store_historical_game_data(game)

        logger.info(f"Ingested {len(upcoming_games)} upcoming games")
        return {
            "status": "success",
            "games_ingested": len(upcoming_games),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error ingesting NBA data: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

def schedule_and_generate_predictions() -> Dict[str, Any]:
    """
    Schedule and generate predictions for upcoming games.

    This function retrieves stored upcoming games, generates predictions
    for those starting within the next 24 hours, and stores them.

    Returns:
        Dict[str, Any]: Summary of generated predictions.
    """
    logger.info("Starting prediction generation for upcoming games")
    try:
        # Get stored games instead of fetching live
        upcoming_games = get_stored_upcoming_games()
        scheduled_count = 0
        now = datetime.now(pytz.UTC)
        prediction_window = now + timedelta(hours=24)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        prediction_model = create_prediction_model()

        for game in upcoming_games:
            game_id = game.get('id')
            game_date_str = game.get('date')
            if not game_id or not game_date_str:
                logger.warning(f"Skipping game with missing ID or date: {game}")
                continue

            try:
                game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
                prediction_time = game_date - timedelta(hours=1)
                if now <= prediction_time <= prediction_window:
                    logger.info(f"Generating prediction for game {game_id}")
                    game_data = loop.run_until_complete(_prepare_game_data(game_id))
                    if not game_data:
                        logger.error(f"Failed to prepare data for game {game_id}")
                        continue

                    # Generate prediction
                    pred_input = PredictionInput(
                        game_id=game_id,
                        home_team=game_data['home_team'],
                        away_team=game_data['away_team'],
                        spread=game_data['spread'],
                        game_date=game_data['game_date'],
                        structured_data=game_data['structured_data'],
                        unstructured_data=game_data['unstructured_data']
                    )
                    prediction_result = loop.run_until_complete(prediction_model.predict(pred_input))

                    # Store prediction
                    prediction_create = PredictionCreate(
                        agent_id=prediction_result.agent_id,
                        game_id=prediction_result.game_id,
                        pick=prediction_result.pick,
                        logic=prediction_result.logic,
                        confidence=prediction_result.confidence,
                        result=prediction_result.result
                    )
                    create_prediction(prediction_create)
                    scheduled_count += 1
            except Exception as e:
                logger.error(f"Error processing game {game_id}: {str(e)}")
                continue

        loop.close()
        logger.info(f"Generated {scheduled_count} predictions")
        return {
            "status": "success",
            "predictions_generated": scheduled_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in prediction scheduling: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def _prepare_game_data(game_id: int) -> Optional[Dict[str, Any]]:
    """
    Prepare all necessary data for a game prediction.

    Args:
        game_id: The ID of the game to prepare data for.

    Returns:
        Optional[Dict[str, Any]]: Game data dictionary or None if preparation fails.
    """
    data_logger = setup_logger("app.workers.tasks.prepare_game_data")
    try:
        data_logger.info(f"Preparing data for game {game_id}")
        game_info = await get_game_by_id(game_id)
        if not game_info:
            data_logger.error(f"Could not find game with ID {game_id}")
            return None

        home_team_id = game_info.get('home_team', {}).get('id')
        away_team_id = game_info.get('visitor_team', {}).get('id')
        home_team_name = game_info.get('home_team', {}).get('name', 'Unknown')
        away_team_name = game_info.get('visitor_team', {}).get('name', 'Unknown')

        # Mocked spread (replace with real odds data in production)
        spread = -3.5  # Home team favored by 3.5 points
        game_date = game_info.get('date', datetime.now().isoformat())

        # Fetch team data concurrently
        home_team_stats, away_team_stats, home_team_news, away_team_news, home_injuries, away_injuries = await asyncio.gather(
            get_team_stats_averages(home_team_id),
            get_team_stats_averages(away_team_id),
            get_recent_news_for_team(home_team_name),
            get_recent_news_for_team(away_team_name),
            get_team_injury_report(home_team_name),
            get_team_injury_report(away_team_name)
        )

        structured_data = {
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_team_stats": home_team_stats.get('data', []),
            "away_team_stats": away_team_stats.get('data', []),
            "spread": spread
        }
        unstructured_data = {
            "home_team_news": home_team_news,
            "away_team_news": away_team_news,
            "home_team_injuries": home_injuries,
            "away_team_injuries": away_injuries
        }

        data_logger.info(f"Successfully prepared data for game {game_id}")
        return {
            "game_id": game_id,
            "home_team": home_team_name,
            "away_team": away_team_name,
            "spread": spread,
            "game_date": game_date,
            "structured_data": structured_data,
            "unstructured_data": unstructured_data
        }
    except Exception as e:
        data_logger.error(f"Error preparing data for game {game_id}: {str(e)}")
        return None