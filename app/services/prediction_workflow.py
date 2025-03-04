"""/**
 * @file: prediction_workflow.py
 * @description 
 * This module orchestrates the simplified predictions workflow for the BadBeats backend.
 * It replaces the Celery-based task system with a single entry point for data ingestion
 * and prediction generation, callable via a script or FastAPI endpoint.
 * 
 * Key features:
 * - Workflow Orchestration: Manages daily data updates and prediction generation.
 * - Simplified Execution: Runs synchronously, suitable for cron or manual triggering.
 * 
 * @dependencies
 * - app.workers.tasks: For data ingestion and prediction logic.
 * - app.core.logger: For logging.
 * 
 * @notes
 * - Designed to run once daily; adjust frequency as needed.
 * - Errors are logged but do not halt execution to ensure partial success.
 * - Assumes Supabase tables are set up via prediction_service.py.
 */"""

from datetime import datetime
from typing import Any, Dict
from app.workers.tasks import ingest_nba_data, schedule_and_generate_predictions
from app.core.logger import setup_logger

# Initialize logger
logger = setup_logger("app.services.prediction_workflow")

def run_prediction_workflow() -> Dict[str, Any]:
    """
    Execute the complete prediction workflow.

    This function:
    1. Ingests latest NBA data into Supabase.
    2. Generates predictions for upcoming games within 24 hours.

    Returns:
        Dict[str, Any]: Summary of the workflow execution.
    """
    logger.info("Starting prediction workflow")
    result = {
        "status": "success",
        "data_ingestion": {},
        "predictions": {},
        "timestamp": datetime.now().isoformat()
    }

    # Step 1: Ingest data
    try:
        ingestion_result = ingest_nba_data()
        result["data_ingestion"] = ingestion_result
        if ingestion_result["status"] != "success":
            logger.warning("Data ingestion encountered issues")
            result["status"] = "partial_success"
    except Exception as e:
        logger.error(f"Data ingestion failed: {str(e)}")
        result["data_ingestion"] = {"status": "error", "message": str(e)}
        result["status"] = "partial_success"

    # Step 2: Generate predictions
    try:
        prediction_result = schedule_and_generate_predictions()
        result["predictions"] = prediction_result
        if prediction_result["status"] != "success":
            logger.warning("Prediction generation encountered issues")
            result["status"] = "partial_success"
    except Exception as e:
        logger.error(f"Prediction generation failed: {str(e)}")
        result["predictions"] = {"status": "error", "message": str(e)}
        result["status"] = "partial_success"

    logger.info(f"Completed prediction workflow with status: {result['status']}")
    return result