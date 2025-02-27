"""
@file: health.py
@description:
Provides a simple health check endpoint to verify that the server
is running and responding.

@dependencies:
- FastAPI APIRouter for route definitions.
- app.core.logger: For component-specific logging

@notes:
- This endpoint is separate from the root endpoint ("/") to follow
  the requirement of having a dedicated route at `/api/v1/health`.
- Additional checks (e.g., database connectivity) can be added here
  if deeper health diagnostics are needed.
"""

from fastapi import APIRouter
from app.core.logger import setup_logger

# Create a component-specific logger
logger = setup_logger("app.api.health")

# Create a new router instance for health checks
router = APIRouter()

@router.get("/health", tags=["Health"])
async def health_check():
    """
    Health Check Endpoint
    
    This endpoint returns a simple JSON object indicating that the service is online.
    It's useful for automated monitoring tools or any system that wants to confirm
    the health of this API.

    Returns:
        dict: A dictionary containing status and message.
    """
    logger.debug("Health check requested")
    return {
        "status": "OK",
        "message": "Health check successful"
    }