"""
@file: celery_app.py
@description:
This module initializes and configures the Celery application for background task processing
and scheduled job execution. It sets up the Celery instance with the appropriate broker,
backend, and task configuration.

@dependencies:
- celery: For asynchronous task processing
- app.core.config: For application configuration settings

@notes:
- The Celery app is configured using settings from the central config module
- Task routes are defined to organize tasks into different queues
- Beat schedule is configured for recurring tasks
- Redis is used as both the broker and result backend
"""

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings
import os

# Initialize Celery app
celery_app = Celery(
    "badbeats",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
)

# Define task routes for better organization
celery_app.conf.task_routes = {
    "app.workers.tasks.generate_prediction": {"queue": "predictions"},
    "app.workers.tasks.update_game_results": {"queue": "results"},
    "app.workers.tasks.ingest_nba_data": {"queue": "data_ingestion"},
    "app.workers.tasks.schedule_game_predictions": {"queue": "schedulers"},
    "app.workers.tasks.check_new_games": {"queue": "schedulers"},
    "app.workers.tasks.reschedule_missed_predictions": {"queue": "schedulers"},
}

# Configure Celery Beat scheduler for periodic tasks
celery_app.conf.beat_schedule = {
    # Data ingestion and game schedule update - every 6 hours
    "fetch-latest-nba-data": {
        "task": "app.workers.tasks.ingest_nba_data",
        "schedule": crontab(hour="*/6", minute="0"),  # Every 6 hours
        "args": (),
    },
    
    # Schedule predictions for upcoming games - every 2 hours
    "schedule-upcoming-game-predictions": {
        "task": "app.workers.tasks.schedule_game_predictions",
        "schedule": crontab(hour="*/2", minute="0"),  # Every 2 hours
        "args": (),
    },
    
    # Update game results after completion - every 3 hours
    "update-game-results": {
        "task": "app.workers.tasks.update_game_results",
        "schedule": crontab(hour="*/3", minute="15"),  # Every 3 hours
        "args": (),
    },
    
    # Check for newly added games - every 12 hours
    "check-new-games": {
        "task": "app.workers.tasks.check_new_games",
        "schedule": crontab(hour="*/12", minute="30"),  # Every 12 hours
        "args": (),
    },
    
    # Rescue missed predictions - every hour
    "rescue-missed-predictions": {
        "task": "app.workers.tasks.reschedule_missed_predictions",
        "schedule": crontab(minute="15"),  # Every hour at 15 minutes past the hour
        "args": (),
    },
}

# This allows the Celery app to work with Pytest
# Ref: https://docs.celeryproject.org/en/stable/userguide/testing.html
if os.environ.get("TESTING"):
    celery_app.conf.update(task_always_eager=True)