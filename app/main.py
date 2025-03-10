"""
Main application entry point for the BadBeats Backend API.

This module initializes the FastAPI application with all necessary configurations,
middleware, and routers. It serves as the central point for running the API service.

The application is structured to follow FastAPI best practices with a modular design.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the Health Router and Predictions Router
from .api.health import router as health_router
from .api.predictions import router as predictions_router
from .api.auth import router as auth_router

# Import middleware setup function
from .core.middleware import setup_all_middleware

# Initialize FastAPI app with metadata
app = FastAPI(
    title="BadBeats API",
    description="Backend API for sports betting predictions powered by AI",
    version="0.1.0",
)

# Configure all middleware (CORS, rate limiting, HTTPS redirect, request logging)
setup_all_middleware(app)

# Root endpoint for basic health check
@app.get("/")
async def root():
    """
    Root endpoint providing a simple health check and API information.

    Returns:
        dict: Basic API information including status and version.
    """
    return {
        "status": "online",
        "api": "BadBeats Backend API",
        "version": "0.1.0"
    }

# Include the health router under prefix /api/v1
app.include_router(health_router, prefix="/api/v1")

# Include the predictions router under prefix /api/v1
app.include_router(predictions_router, prefix="/api/v1")

# Include the authentication router under prefix /api/v1/auth
app.include_router(auth_router, prefix="/api/v1/auth")


# Add favicon endpoint to silence 404s
@app.get('/favicon.ico')
async def favicon():
    """
    Empty favicon endpoint to silence 404 errors.
    """
    return {}

if __name__ == "__main__":
    # Run the API with uvicorn when script is executed directly
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)