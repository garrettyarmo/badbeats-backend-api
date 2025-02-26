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
}

# Beat schedule configuration for periodic tasks
beat_schedule = {
    "fetch-latest-nba-data": {
        "task": "app.workers.tasks.ingest_nba_data",
        "schedule": crontab(hour="*/6", minute="0"),  # Every 6 hours
        "args": (),
    },
    "schedule-upcoming-game-predictions": {
        "task": "app.workers.tasks.schedule_game_predictions",
        "schedule": crontab(hour="*/2", minute="0"),  # Every 2 hours
        "args": (),
    },
    "update-game-results": {
        "task": "app.workers.tasks.update_game_results",
        "schedule": crontab(hour="*/3", minute="15"),  # Every 3 hours
        "args": (),
    }
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