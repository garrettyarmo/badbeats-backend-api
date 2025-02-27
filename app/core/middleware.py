"""
@file: middleware.py
@description:
This module configures and centralizes middleware for the FastAPI application.
It includes CORS policy configuration and rate limiting middleware to prevent API abuse.

The middleware components include:
- CORS configuration: Controls which domains can access the API
- Rate limiting: Prevents abuse by limiting the number of requests per time period
- Request logging: Logs information about each request and its processing time
- HTTPS redirect: Ensures secure connections in production

@dependencies:
- fastapi: For CORSMiddleware
- fastapi_limiter: For rate limiting
- redis: As a backend for rate limiting
- app.core.config: For application settings
- app.core.logger: For structured logging

@notes:
- CORS is configured differently for development vs. production environments
- Rate limiting is applied to all API routes, with specific exemptions for internal routes
- Rate limits are configurable via environment variables
- Middleware is applied in the main FastAPI application
"""

import asyncio
import time
from typing import Callable, List, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as redis
import fastapi_limiter
from fastapi_limiter.depends import RateLimiter

from app.core.config import settings
from app.core.logger import setup_logger, log_request_details

# Create a component-specific logger
logger = setup_logger("app.core.middleware")


def setup_cors(app: FastAPI) -> None:
    """
    Configure CORS middleware for the FastAPI application.
    
    In development mode, this allows all origins, headers, and methods.
    In production, only specified origins are allowed.
    
    Args:
        app: The FastAPI application instance
    """
    # Default CORS settings for development
    origins = ["*"]
    
    # More restrictive CORS settings for production
    if settings.APP_ENV == "production":
        # In production, specify allowed origins explicitly
        # Replace these with your actual frontend domains
        origins = [
            "https://badbeats.org",
            "https://badbeats.vercel.app/"
        ]
        
        # Allow localhost for testing and development
        if settings.DEBUG:
            origins.extend([
                "http://localhost",
                "http://localhost:3000",
                "http://localhost:8000",
            ])
    
    logger.info(f"Setting up CORS middleware with origins: {origins}")
    
    # Add the CORS middleware to the application
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        max_age=86400,  # 24 hours cache for preflight requests
    )


async def setup_rate_limiting(app: FastAPI) -> None:
    """
    Configure rate limiting middleware for the FastAPI application.
    
    This protects the API from abuse by limiting the number of requests
    per time period for each client, identified by their IP address.
    
    Args:
        app: The FastAPI application instance
    """
    try:
        # Initialize Redis connection for rate limiting
        redis_instance = redis.from_url(
            settings.REDIS_URL, 
            encoding="utf-8", 
            decode_responses=True
        )
        
        # Test Redis connection
        await redis_instance.ping()
        
        # Initialize the rate limiter with Redis backend
        await fastapi_limiter.FastAPILimiter.init(redis_instance)
        
        logger.info("Rate limiting middleware initialized successfully")
        
        # Apply rate limiting to routes that need protection
        # This is done via dependencies in the route definitions
        
    except Exception as e:
        logger.error(f"Failed to initialize rate limiting: {str(e)}")
        logger.warning("API will run without rate limiting protection")


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect HTTP requests to HTTPS in production.
    
    This ensures that all API requests use secure HTTPS connections
    when the application is running in production mode.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request and redirect to HTTPS if needed.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware in the chain
            
        Returns:
            Response: Either a redirect response or the original response
        """
        # Only redirect in production
        if settings.APP_ENV == "production":
            # Check if the request is using HTTP (not HTTPS)
            if request.url.scheme == "http":
                # Get the same URL but with HTTPS scheme
                https_url = str(request.url).replace("http://", "https://", 1)
                
                # Create a redirect response
                from starlette.responses import RedirectResponse
                logger.debug(f"Redirecting HTTP request to HTTPS: {https_url}")
                return RedirectResponse(
                    https_url, 
                    status_code=301  # Permanent redirect
                )
        
        # For HTTPS requests or non-production environments, continue normally
        return await call_next(request)


def setup_https_redirect(app: FastAPI) -> None:
    """
    Add HTTPS redirect middleware to the FastAPI application.
    
    This is only active in production mode.
    
    Args:
        app: The FastAPI application instance
    """
    if settings.APP_ENV == "production":
        logger.info("Setting up HTTPS redirect middleware for production")
        app.add_middleware(HTTPSRedirectMiddleware)
    else:
        logger.debug("HTTPS redirect middleware not added (not in production mode)")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging API requests and their processing time.
    
    This logs information about each request including:
    - HTTP method
    - URL path
    - Client IP
    - Status code
    - Processing time
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process each request and log details about it.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware in the chain
            
        Returns:
            Response: The response from downstream middleware
        """
        # Record start time
        start_time = time.time()
        
        # Get client IP - this handles cases where the app is behind a proxy
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log request details using the structured logging function
        log_request_details(logger, request, process_time, response.status_code)
        
        return response


def setup_request_logging(app: FastAPI) -> None:
    """
    Add request logging middleware to the FastAPI application.
    
    Args:
        app: The FastAPI application instance
    """
    logger.info("Setting up request logging middleware")
    app.add_middleware(RequestLoggingMiddleware)


def setup_all_middleware(app: FastAPI) -> None:
    """
    Configure and add all middleware to the FastAPI application.
    
    This is the main function that should be called from the application
    startup code to set up all middleware components.
    
    Args:
        app: The FastAPI application instance
    """
    # Setup CORS first (outermost middleware)
    setup_cors(app)
    
    # Setup request logging
    setup_request_logging(app)
    
    # Setup HTTPS redirect for production
    setup_https_redirect(app)
    
    # Register an event handler to setup rate limiting
    # This needs to be done asynchronously so we register it as a startup event
    @app.on_event("startup")
    async def initialize_rate_limiter():
        await setup_rate_limiting(app)
        logger.info("All middleware initialized successfully")