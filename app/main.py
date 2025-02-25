"""
Main application entry point for the BadBeats Backend API.

This module initializes the FastAPI application with all necessary configurations,
middleware, and routers. It serves as the central point for running the API service.

The application is structured to follow FastAPI best practices with a modular design.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app with metadata
app = FastAPI(
    title="BadBeats API",
    description="Backend API for sports betting predictions powered by AI",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Import and include API routers here
# Example: app.include_router(some_router, prefix="/api/v1")

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