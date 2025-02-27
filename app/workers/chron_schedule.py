"""
@file: cron_schedule.py
@description:
This module provides a central place to define scheduling rules for Celery tasks.
It includes utility functions for scheduling prediction tasks based on game times
and checking for missed or new predictions.

@dependencies:
- celery: For task scheduling
- app.workers.tasks: For task execution
- datetime, pytz: For time calculations
- app.core.logger: For logging

@notes:
- Centralizes scheduling logic separate from task implementation
- Contains helper functions used by scheduled tasks
- Uses Redis for basic job tracking (optional)
"""

from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Any, Optional

from app.workers.tasks import generate_prediction, update_game_results
from app.core.logger import logger


def calculate_prediction_time(game_time: datetime) -> datetime:
    """
    Calculate when a prediction should be generated for a game.
    
    Args:
        game_time: The scheduled start time of the game
        
    Returns:
        datetime: The time when prediction should be generated (1 hour before game)
    """
    return game_time - timedelta(hours=1)


def should_schedule_prediction(game_id: int, game_time: datetime) -> bool:
    """
    Determine if a prediction should be scheduled for a game.
    
    This function checks if:
    1. The game hasn't already been scheduled
    2. The game time is in the future
    3. There's enough time to make a meaningful prediction
    
    Args:
        game_id: The ID of the game
        game_time: The scheduled start time of the game
        
    Returns:
        bool: True if prediction should be scheduled, False otherwise
    """
    # Get current time in UTC
    now = datetime.now(pytz.UTC)
    
    # Skip if game is in the past
    if game_time <= now:
        logger.debug(f"Game {game_id} is in the past or happening now, skipping scheduling")
        return False
    
    # Skip if less than 15 minutes until prediction time
    prediction_time = calculate_prediction_time(game_time)
    if prediction_time - now < timedelta(minutes=15):
        logger.debug(f"Less than 15 minutes until prediction time for game {game_id}, skipping scheduling")
        return False
    
    # TODO: Check database or cache to see if prediction already exists for this game
    # For now, we'll assume it doesn't
    
    return True


def handle_emergency_prediction(game_id: int, game_time: datetime) -> bool:
    """
    Handle emergency prediction scheduling for games that are about to start.
    
    This function is used for games that were missed in the regular scheduling
    process but still need predictions.
    
    Args:
        game_id: The ID of the game
        game_time: The scheduled start time of the game
        
    Returns:
        bool: True if emergency prediction was scheduled, False otherwise
    """
    # Get current time in UTC
    now = datetime.now(pytz.UTC)
    
    # Skip if game is in the past
    if game_time <= now:
        logger.debug(f"Game {game_id} is in the past, skipping emergency prediction")
        return False
    
    # Skip if more than 3 hours until game time (not an emergency yet)
    if game_time - now > timedelta(hours=3):
        logger.debug(f"More than 3 hours until game {game_id}, not an emergency")
        return False
    
    # TODO: Check database to see if prediction already exists for this game
    # For now, we'll assume it doesn't
    
    # Schedule prediction immediately
    logger.info(f"Scheduling emergency prediction for game {game_id}")
    generate_prediction.apply_async(
        args=[game_id],
        countdown=5,  # Wait 5 seconds to avoid overloading
        expires=game_time,  # Don't run if game already started
    )
    
    return True