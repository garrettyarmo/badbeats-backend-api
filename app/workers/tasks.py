"""
@file: tasks.py
@description:
This module contains Celery tasks for the BadBeats backend, focusing on scheduling
and executing AI-driven predictions for NBA games. The tasks handle:
- Data ingestion from NBA API and news sources
- Scheduling predictions to run one hour before each game
- Generating predictions using the LangChain model
- Updating prediction results after games

@dependencies:
- celery: For task definition and execution
- datetime: For time calculations and scheduling
- app.workers.celery_app: For Celery instance
- app.services.ball_dont_lie_api: For fetching NBA data
- app.services.news_ingestion: For fetching news data
- app.llm.langchain_model: For prediction generation
- app.services.prediction_service: For storing predictions
- app.schemas.predictions: For data validation
- app.core.logger: For logging

@notes:
- Tasks use retry mechanisms for resilience
- Games are scheduled for prediction one hour before start time
- The module includes helper functions for data preparation
- Error handling logs issues but allows the application to continue
"""

import asyncio
from celery import shared_task, chain, group
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import pytz
from tenacity import retry, stop_after_attempt, wait_exponential

from app.workers.celery_app import celery_app
from app.services.ball_dont_lie_api import (
    get_upcoming_games,
    get_game_by_id,
    get_team_by_id,
    get_team_stats_averages
)
from app.services.news_ingestion import (
    get_recent_news_for_team,
    get_team_injury_report
)
from app.services.prediction_service import create_prediction
from app.llm.langchain_model import create_langchain_prediction_model
from app.llm.base_model import PredictionInput
from app.schemas.predictions import PredictionCreate
from app.core.logger import logger


@shared_task(
    bind=True,
    name="app.workers.tasks.ingest_nba_data",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    acks_late=True
)
def ingest_nba_data(self):
    """
    Task to ingest NBA data from external APIs.
    
    This task fetches the latest NBA game data, team stats, and news
    for use in the prediction models.
    
    Returns:
        dict: Summary of ingested data
    """
    try:
        # Create a new event loop for asyncio operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Fetch upcoming games
        upcoming_games = loop.run_until_complete(get_upcoming_games(days_ahead=7))
        loop.close()
        
        logger.info(f"Ingested {len(upcoming_games)} upcoming games")
        return {
            "status": "success",
            "games_ingested": len(upcoming_games),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error ingesting NBA data: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name="app.workers.tasks.schedule_game_predictions",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    acks_late=True
)
def schedule_game_predictions(self):
    """
    Task to schedule prediction tasks for upcoming games.
    
    This task scans upcoming games and schedules predictions
    to run one hour before each game's start time.
    
    Returns:
        dict: Summary of scheduled predictions
    """
    try:
        # Create a new event loop for asyncio operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Fetch upcoming games
        upcoming_games = loop.run_until_complete(get_upcoming_games(days_ahead=7))
        loop.close()
        
        scheduled_count = 0
        for game in upcoming_games:
            try:
                # Parse game start time
                game_date_str = game.get('date')
                if not game_date_str:
                    logger.warning(f"Game ID {game.get('id')} has no date")
                    continue
                
                # Parse the date string to datetime object
                # Format varies but typically: "2023-02-15T00:00:00.000Z"
                game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
                
                # Calculate when to run the prediction (1 hour before game start)
                prediction_time = game_date - timedelta(hours=1)
                current_time = datetime.now(pytz.UTC)
                
                if prediction_time > current_time:
                    # Schedule the prediction task
                    eta = prediction_time
                    
                    # Extract team information
                    home_team = game.get('home_team', {}).get('name', 'Unknown')
                    away_team = game.get('visitor_team', {}).get('name', 'Unknown')
                    
                    logger.info(
                        f"Scheduling prediction for game {game.get('id')}: "
                        f"{away_team} @ {home_team} at {eta.isoformat()}"
                    )
                    
                    # Schedule the generate_prediction task with ETA
                    generate_prediction.apply_async(
                        args=[game.get('id')],
                        eta=eta,
                        retry=True,
                        retry_policy={
                            'max_retries': 3,
                            'interval_start': 0,
                            'interval_step': 0.2,
                            'interval_max': 0.6,
                        }
                    )
                    
                    scheduled_count += 1
            except Exception as e:
                logger.error(f"Error scheduling prediction for game {game.get('id')}: {str(e)}")
                continue
        
        logger.info(f"Scheduled {scheduled_count} game predictions")
        return {
            "status": "success",
            "predictions_scheduled": scheduled_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error scheduling game predictions: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name="app.workers.tasks.generate_prediction",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 300},
    acks_late=True
)
def generate_prediction(self, game_id: int):
    """
    Task to generate a prediction for a specific game.
    
    This task fetches all necessary data for a game and
    runs the LangChain prediction model to generate a prediction.
    
    Args:
        game_id: The ID of the game to generate a prediction for
        
    Returns:
        dict: Summary of the generated prediction
    """
    try:
        # Create a new event loop for asyncio operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Prepare game data for prediction
        game_data = loop.run_until_complete(_prepare_game_data(game_id))
        
        if not game_data:
            logger.error(f"Failed to gather data for game {game_id}")
            return {
                "status": "error",
                "message": f"Failed to gather data for game {game_id}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Initialize the prediction model
        prediction_model = create_langchain_prediction_model()
        
        # Create prediction input
        prediction_input = PredictionInput(
            game_id=game_id,
            home_team=game_data['home_team'],
            away_team=game_data['away_team'],
            spread=game_data['spread'],
            game_date=game_data['game_date'],
            structured_data=game_data['structured_data'],
            unstructured_data=game_data['unstructured_data']
        )
        
        # Generate prediction (async)
        prediction_result = loop.run_until_complete(prediction_model.predict(prediction_input))
        loop.close()
        
        # Save the prediction to the database
        prediction_create = PredictionCreate(
            agent_id=prediction_result.agent_id,
            game_id=prediction_result.game_id,
            pick=prediction_result.pick,
            logic=prediction_result.logic,
            confidence=prediction_result.confidence,
            result=prediction_result.result
        )
        
        saved_prediction = create_prediction(prediction_create)
        
        logger.info(f"Generated prediction for game {game_id}: {saved_prediction.pick}")
        return {
            "status": "success",
            "game_id": game_id,
            "pick": saved_prediction.pick,
            "confidence": saved_prediction.confidence,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating prediction for game {game_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    name="app.workers.tasks.update_game_results",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 60},
    acks_late=True
)
def update_game_results(self):
    """
    Task to update the results of completed games.
    
    This task checks completed games, determines if predictions were correct,
    and updates the prediction results in the database.
    
    Returns:
        dict: Summary of updated results
    """
    # This task would fetch completed games, compare actual results with predictions
    # and update the "result" field from "pending" to "win" or "loss"
    # Implementation would depend on how we track game results and determine winners
    # For now, this is a placeholder
    
    logger.info("Updating game results (placeholder implementation)")
    return {
        "status": "success",
        "message": "Game results update not yet implemented",
        "timestamp": datetime.now().isoformat()
    }


async def _prepare_game_data(game_id: int) -> Optional[Dict[str, Any]]:
    """
    Helper function to prepare all necessary data for a game prediction.
    
    This function gathers structured and unstructured data for both teams
    in a game, including team stats, recent news, and injury reports.
    
    Args:
        game_id: The ID of the game to prepare data for
        
    Returns:
        Optional[Dict[str, Any]]: Dictionary with all game data or None if data gathering fails
    """
    try:
        # Fetch basic game information
        game_info = await get_game_by_id(game_id)
        if not game_info:
            logger.error(f"Could not find game with ID {game_id}")
            return None
        
        # Extract team information
        home_team_id = game_info.get('home_team', {}).get('id')
        away_team_id = game_info.get('visitor_team', {}).get('id')
        home_team_name = game_info.get('home_team', {}).get('name', 'Unknown')
        away_team_name = game_info.get('visitor_team', {}).get('name', 'Unknown')
        
        # Mocked spread for now (would come from odds API in a real implementation)
        # Positive means home team is underdog, negative means home team is favorite
        spread = -3.5  # Example: home team favored by 3.5 points
        
        # Game date and time
        game_date = game_info.get('date', datetime.now().isoformat())
        
        # Gather team data concurrently
        home_team_stats, away_team_stats, home_team_news, away_team_news, home_injuries, away_injuries = await asyncio.gather(
            get_team_stats_averages(home_team_id),
            get_team_stats_averages(away_team_id),
            get_recent_news_for_team(home_team_name),
            get_recent_news_for_team(away_team_name),
            get_team_injury_report(home_team_name),
            get_team_injury_report(away_team_name)
        )
        
        # Prepare structured data
        structured_data = {
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_team_stats": home_team_stats.get('data', []),
            "away_team_stats": away_team_stats.get('data', []),
            "spread": spread
        }
        
        # Prepare unstructured data
        unstructured_data = {
            "home_team_news": home_team_news,
            "away_team_news": away_team_news,
            "home_team_injuries": home_injuries,
            "away_team_injuries": away_injuries
        }
        
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
        logger.error(f"Error preparing data for game {game_id}: {str(e)}")
        return None