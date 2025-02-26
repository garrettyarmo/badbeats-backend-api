"""
Workers Package for BadBeats Backend.

This package handles all background and scheduled tasks using Celery, including:
- Data ingestion jobs
- Prediction scheduling
- Result updates
- Cleanup operations

Key components:
- celery_app: Initializes and configures the Celery application
- tasks: Defines the Celery tasks for prediction scheduling and data ingestion
- worker: Entry point for starting Celery workers
"""

from app.workers.celery_app import celery_app
from app.workers.tasks import (
    ingest_nba_data,
    schedule_game_predictions,
    generate_prediction,
    update_game_results
)

__all__ = [
    'celery_app',
    'ingest_nba_data',
    'schedule_game_predictions',
    'generate_prediction',
    'update_game_results'
]