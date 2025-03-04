"""
/**
 * @file: prediction_workflow.py
 * @description 
 * This module provides entry points for running data ingestion and prediction generation workflows
 * in the BadBeats backend. It orchestrates these processes separately, allowing data ingestion to
 * update the database daily and prediction generation to run periodically (e.g., hourly) closer to
 * game times.
 * 
 * Key features:
 * - Data Ingestion Workflow: Triggers daily data updates from the Ball Don't Lie API.
 * - Prediction Generation Workflow: Triggers prediction generation for upcoming games.
 * 
 * @dependencies
 * - app.workers.tasks: For ingestion and prediction logic.
 * - app.core.logger: For logging.
 * 
 * @notes
 * - Designed for external scheduling (e.g., cron) with separate triggers.
 * - Synchronous execution simplifies deployment without Celery.
 */
"""
from app.workers.tasks import ingest_nba_data, generate_predictions
from app.core.logger import setup_logger

logger = setup_logger("app.services.prediction_workflow")

def run_data_ingestion():
    """
    Run the data ingestion workflow to update NBA data in Supabase.

    Intended to be scheduled daily to keep the database current.
    """
    logger.info("Running data ingestion workflow")
    result = ingest_nba_data()
    logger.info(f"Data ingestion completed with status: {result['status']}")

def run_prediction_generation():
    """
    Run the prediction generation workflow for upcoming games.

    Intended to be scheduled periodically (e.g., hourly) to generate predictions
    for games within the next hour.
    """
    logger.info("Running prediction generation workflow")
    result = generate_predictions()
    logger.info(f"Prediction generation completed with status: {result['status']}")