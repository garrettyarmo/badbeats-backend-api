"""
@file: celery_config.py
@description:
This module provides Celery-specific configuration settings, separate from
the main application configuration. It includes queue definitions, task
routing, and other Celery-specific settings.

@dependencies:
- celery: For task queuing and background processing
- app.core.config: For main application configuration

@notes:
- All Celery-specific configurations should be defined here
- This centralizes Celery settings and makes them easier to maintain
- Queue names and routing patterns are defined here
"""

from celery.schedules import crontab

# Queue definitions
QUEUE_DEFAULT = "default"
QUEUE_PREDICTIONS = "predictions"
QUEUE_RESULTS = "results"
QUEUE_DATA_INGESTION = "data_ingestion"
QUEUE_SCHEDULERS = "schedulers"

# Task routing configuration
task_routes = {
    "app.workers.tasks.generate_prediction": {"queue": QUEUE_PREDICTIONS},
    "app.workers.tasks.update_game_results": {"queue": QUEUE_RESULTS},
    "app.workers.tasks.ingest_nba_data": {"queue": QUEUE_DATA_INGESTION},
    "app.workers.tasks.schedule_game_predictions": {"queue": QUEUE_SCHEDULERS},
    "app.workers.tasks.check_new_games": {"queue": QUEUE_SCHEDULERS},
    "app.workers.tasks.reschedule_missed_predictions": {"queue": QUEUE_SCHEDULERS},
}

# Beat schedule configuration for periodic tasks
beat_schedule = {
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

# Worker configuration
worker_prefetch_multiplier = 1
task_acks_late = True
task_reject_on_worker_lost = True
task_track_started = True

# Serialization configuration
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"

# Time zone configuration
timezone = "UTC"
enable_utc = True