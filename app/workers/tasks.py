"""
/**
 * @file: tasks.py
 * @description 
 * This module contains utility functions for managing the predictions workflow in the BadBeats backend.
 * It provides separate functions for data ingestion and prediction generation, allowing them to run
 * independently at different times. Data ingestion fetches and stores NBA data daily, while prediction
 * generation uses stored data to produce betting picks closer to game times.
 * 
 * Key features:
 * - Data Ingestion: Fetches comprehensive NBA game data and stats, storing them in Supabase daily.
 * - Prediction Generation: Generates predictions using stored structured data and fresh unstructured data.
 * - Helper Functions: Supports data retrieval and stats computation from stored data.
 * 
 * @dependencies
 * - asyncio: For asynchronous operations.
 * - datetime: For time calculations.
 * - pytz: For timezone handling.
 * - app.services.ball_dont_lie_api: For NBA data fetching.
 * - app.services.news_ingestion: For news and injury data.
 * - app.llm.prediction_model: For prediction generation.
 * - app.services.prediction_service: For database interactions.
 * - app.schemas.predictions: For data validation.
 * - app.core.logger: For logging.
 * 
 * @notes
 * - Designed for cron-based scheduling: ingestion daily, predictions hourly.
 * - Structured data is pre-fetched to reduce API calls during prediction.
 * - Error handling ensures partial failures don't halt the process.
 */
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pytz

from app.services.ball_dont_lie_api import (
    get_games,
    get_stats,
    get_team_by_name
)
from app.services.news_ingestion import (
    get_recent_news_for_team,
    get_team_injury_report
)
from app.services.prediction_service import (
    store_historical_game_data,
    get_stored_upcoming_games,
    create_prediction
)
from app.llm.prediction_model import create_prediction_model, PredictionInput
from app.schemas.predictions import PredictionCreate
from app.core.logger import setup_logger
from app.db.supabase_client import supabase

# Initialize logger
logger = setup_logger("app.workers.tasks")

def get_current_season() -> int:
    """
    Determine the current NBA season based on the current date.

    Returns:
        int: The current season year (e.g., 2023 for the 2023-24 season).

    Notes:
        - NBA season typically starts in late October; before July, it's the previous year.
    """
    now = datetime.now()
    return now.year if now.month >= 7 else now.year - 1

async def ingest_nba_data_async() -> Dict[str, Any]:
    """
    Asynchronously ingest NBA data from the Ball Don't Lie API and store it in Supabase.

    Fetches all games for the current season, including stats for past games, and stores them.

    Returns:
        Dict[str, Any]: Summary of ingested data with status and count.
    """
    logger.info("Starting NBA data ingestion")
    try:
        current_season = get_current_season()
        games = await get_games(seasons=[current_season], fetch_all_pages=True)
        ingested_count = 0

        for game in games:
            game_data = {"game_info": game}
            if game.get('status') == 'Final':  # Past game with completed stats
                stats = await get_stats(game_ids=[game['id']])
                game_data["stats"] = stats
            store_historical_game_data(game_data)
            ingested_count += 1

        logger.info(f"Ingested {ingested_count} games")
        return {
            "status": "success",
            "games_ingested": ingested_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error ingesting NBA data: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

def ingest_nba_data() -> Dict[str, Any]:
    """
    Synchronous wrapper for NBA data ingestion.

    Returns:
        Dict[str, Any]: Result of the ingestion process.
    """
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(ingest_nba_data_async())
    loop.close()
    return result

async def generate_predictions_async() -> Dict[str, Any]:
    """
    Asynchronously generate predictions for upcoming games within the next hour.

    Uses stored structured data and fetches fresh unstructured data for predictions.

    Returns:
        Dict[str, Any]: Summary of generated predictions.
    """
    logger.info("Starting prediction generation")
    try:
        upcoming_games = get_stored_upcoming_games()
        prediction_model = create_prediction_model()
        generated_count = 0
        now = datetime.now(pytz.UTC)
        prediction_window = now + timedelta(hours=1)

        for game in upcoming_games:
            game_id = game.get('id')
            game_date_str = game.get('game_info', {}).get('date')
            if not game_id or not game_date_str:
                logger.warning(f"Skipping game with missing ID or date: {game}")
                continue

            game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
            prediction_time = game_date - timedelta(hours=1)
            if now <= prediction_time <= prediction_window:
                game_data = await _prepare_game_data(game_id)
                if not game_data:
                    logger.error(f"Failed to prepare data for game {game_id}")
                    continue

                pred_input = PredictionInput(**game_data)
                prediction_result = await prediction_model.predict(pred_input)

                prediction_create = PredictionCreate(
                    agent_id=prediction_result.agent_id,
                    game_id=prediction_result.game_id,
                    pick=prediction_result.pick,
                    logic=prediction_result.logic,
                    confidence=prediction_result.confidence,
                    result=prediction_result.result
                )
                create_prediction(prediction_create)
                generated_count += 1
                logger.info(f"Generated prediction for game {game_id}: {prediction_result.pick}")

        logger.info(f"Generated {generated_count} predictions")
        return {
            "status": "success",
            "predictions_generated": generated_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in prediction generation: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

def generate_predictions() -> Dict[str, Any]:
    """
    Synchronous wrapper for prediction generation.

    Returns:
        Dict[str, Any]: Result of the prediction process.
    """
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(generate_predictions_async())
    loop.close()
    return result

async def _prepare_game_data(game_id: int) -> Optional[Dict[str, Any]]:
    """
    Prepare data for prediction using stored structured data and fresh unstructured data.

    Args:
        game_id: The ID of the game to prepare data for.

    Returns:
        Optional[Dict[str, Any]]: Prepared game data or None if preparation fails.
    """
    try:
        # Retrieve game from database
        response = supabase.table("games").select("*").eq("id", str(game_id)).execute()
        if not response.data:
            logger.error(f"Game {game_id} not found in database")
            return None
        game = response.data[0]
        game_info = game['game_data']['game_info']

        home_team_id = game_info['home_team']['id']
        away_team_id = game_info['visitor_team']['id']
        home_team_name = game_info['home_team']['name']
        away_team_name = game_info['visitor_team']['name']
        game_date = datetime.fromisoformat(game_info['date'])

        # Get recent games and compute stats
        N = 5  # Last 5 games for stats
        home_recent_games = get_recent_games_from_db(home_team_id, game_date, N)
        away_recent_games = get_recent_games_from_db(away_team_id, game_date, N)
        home_avg_stats = compute_avg_stats(home_recent_games, home_team_id)
        away_avg_stats = compute_avg_stats(away_recent_games, away_team_id)

        # Fetch unstructured data
        home_news, away_news, home_injuries, away_injuries = await asyncio.gather(
            get_recent_news_for_team(home_team_name),
            get_recent_news_for_team(away_team_name),
            get_team_injury_report(home_team_name),
            get_team_injury_report(away_team_name)
        )

        structured_data = {
            "home_team_stats": home_avg_stats,
            "away_team_stats": away_avg_stats,
        }
        unstructured_data = {
            "home_team_news": home_news,
            "away_team_news": away_news,
            "home_team_injuries": home_injuries,
            "away_team_injuries": away_injuries
        }

        return {
            "game_id": game_id,
            "home_team": home_team_name,
            "away_team": away_team_name,
            "spread": 0.0,  # Placeholder; implement odds fetching
            "game_date": game_info['date'],
            "structured_data": structured_data,
            "unstructured_data": unstructured_data
        }
    except Exception as e:
        logger.error(f"Error preparing data for game {game_id}: {str(e)}")
        return None

def get_recent_games_from_db(team_id: int, before_date: datetime, limit: int) -> List[Dict[str, Any]]:
    """
    Retrieve the last N games for a team from the database before a specified date.

    Args:
        team_id: The ID of the team.
        before_date: The cutoff date for games.
        limit: Number of recent games to retrieve.

    Returns:
        List[Dict[str, Any]]: List of game data dictionaries.
    """
    try:
        response = supabase.table("games").select("*").lt(
            "game_data->game_info->date", before_date.isoformat()
        ).or_(
            f"game_data->game_info->home_team->id.eq.{team_id},game_data->game_info->visitor_team->id.eq.{team_id}"
        ).order("game_data->game_info->date", desc=True).limit(limit).execute()

        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Error retrieving recent games for team {team_id}: {str(e)}")
        return []

def compute_avg_stats(games: List[Dict[str, Any]], team_id: int) -> Dict[str, float]:
    """
    Compute average statistics from a list of games for a specific team.

    Args:
        games: List of game data dictionaries with stats.
        team_id: The ID of the team to compute stats for.

    Returns:
        Dict[str, float]: Dictionary of averaged stats (e.g., points, rebounds).
    """
    if not games:
        return {"points": 0.0, "rebounds": 0.0, "assists": 0.0}

    total_stats = {"points": 0, "rebounds": 0, "assists": 0}
    game_count = 0

    for game in games:
        stats = game.get('game_data', {}).get('stats', [])
        if not stats:
            continue

        game_stats = {"points": 0, "rebounds": 0, "assists": 0}
        for stat in stats:
            if stat.get('team', {}).get('id') == team_id:
                game_stats["points"] += stat.get('pts', 0)
                game_stats["rebounds"] += stat.get('reb', 0)
                game_stats["assists"] += stat.get('ast', 0)

        if game_stats["points"] > 0:  # Ensure valid game data
            for key in total_stats:
                total_stats[key] += game_stats[key]
            game_count += 1

    if game_count == 0:
        return {"points": 0.0, "rebounds": 0.0, "assists": 0.0}

    return {key: value / game_count for key, value in total_stats.items()}