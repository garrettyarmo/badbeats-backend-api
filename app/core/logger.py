"""
@file: logger.py
@description:
This module provides a unified logging system for the BadBeats API, supporting:
- Color-coded console output for different log levels
- Structured logging for easier parsing and analysis
- Consistent logging format across the application
- Configurable log levels based on environment settings

The module creates a default logger instance that can be imported and used
throughout the application, ensuring consistent logging patterns.

@dependencies:
- logging: Standard Python logging module
- sys: For stdout access
- typing: For type annotations
- colorama: For cross-platform colored terminal text
- app.core.config: For logging configuration settings (optional)

@notes:
- Colors are automatically disabled if output is not to a terminal
- Default log level is read from environment variables via settings
- The ColoredFormatter class adds ANSI color codes based on log level
- This implementation uses a singleton pattern for the logger
"""

import logging
import sys
import os
from typing import Optional, Dict, Any
from datetime import datetime

# Import colorama for cross-platform color support
try:
    from colorama import init, Fore, Back, Style
    # Initialize colorama
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

# Try to import settings, but provide defaults if not available
try:
    from app.core.config import settings
    DEFAULT_LOG_LEVEL = settings.LOG_LEVEL
except ImportError:
    DEFAULT_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log messages based on level.
    
    This formatter enhances log readability by using different colors
    for different logging levels, making it easier to spot warnings
    and errors in the console output.
    """
    
    if COLORAMA_AVAILABLE:
        COLORS = {
            logging.DEBUG: Fore.CYAN,       # Cyan for debug messages
            logging.INFO: Fore.GREEN,       # Green for info messages
            logging.WARNING: Fore.YELLOW,   # Yellow for warnings
            logging.ERROR: Fore.RED,        # Red for errors
            logging.CRITICAL: Fore.WHITE + Back.RED,  # White on red background for critical errors
        }
    else:
        # Fallback to ANSI escape codes if colorama is not available
        COLORS = {
            logging.DEBUG: '\033[36m',      # Cyan
            logging.INFO: '\033[32m',       # Green
            logging.WARNING: '\033[33m',    # Yellow
            logging.ERROR: '\033[31m',      # Red
            logging.CRITICAL: '\033[41m',   # Red background
        }
    
    RESET = '\033[0m' if not COLORAMA_AVAILABLE else ''
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record with appropriate color based on its level.
        
        Args:
            record: The log record to format
            
        Returns:
            str: The colored formatted log message
        """
        # Store the original format
        original_format = self._style._fmt
        
        # Get the color for this log level
        color = self.COLORS.get(record.levelno, self.RESET)
        
        # Add timestamp info if not already in the format
        if '%(asctime)s' not in original_format:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            record.asctime = timestamp
        
        # Add the color to the message
        if COLORAMA_AVAILABLE:
            # Let colorama handle the coloring and resetting
            record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
            record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        else:
            # Manually add ANSI color codes
            record.levelname = f"{color}{record.levelname}{self.RESET}"
            record.msg = f"{color}{record.msg}{self.RESET}"
        
        # Return the formatted string
        return super().format(record)


def get_console_handler() -> logging.StreamHandler:
    """
    Create and configure a console handler with colored output.
    
    Returns:
        logging.StreamHandler: Configured console handler
    """
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Define the log format with colors
    log_format = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    formatter = ColoredFormatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
    
    console_handler.setFormatter(formatter)
    return console_handler


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get or create a logger with the specified name and level.
    
    Args:
        name: The logger name, typically __name__ or a module path
        level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, uses the default from environment settings
               
    Returns:
        logging.Logger: Configured logger instance
    """
    # Convert level string to logging constant
    if level is None:
        level = DEFAULT_LOG_LEVEL
        
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")
    
    # Get or create the logger
    logger = logging.getLogger(name)
    
    # Only add handlers if this logger doesn't have any
    if not logger.handlers:
        logger.setLevel(numeric_level)
        logger.addHandler(get_console_handler())
        logger.propagate = False
    
    return logger


def setup_logger(name: str = "app", level: Optional[str] = None) -> logging.Logger:
    """
    Set up and configure a logger with colored output.
    
    This is the main function that should be called to create loggers
    throughout the application.
    
    Args:
        name: The name of the logger
        level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If None, uses the default from environment settings
               
    Returns:
        logging.Logger: Configured logger instance
    """
    return get_logger(name, level)


def log_request_details(logger: logging.Logger, request: Any, response_time: float, status_code: int) -> None:
    """
    Log details about an HTTP request and its response.
    
    Args:
        logger: The logger to use
        request: The request object (expected to have method and url attributes)
        response_time: The time taken to process the request in seconds
        status_code: The HTTP status code of the response
    """
    try:
        # Format the log message with request details
        method = getattr(request, 'method', 'UNKNOWN')
        url = getattr(request, 'url', 'UNKNOWN')
        
        # Determine log level based on status code
        if status_code >= 500:
            log_level = logging.ERROR
            logger.error(f"{method} {url} completed with status {status_code} in {response_time:.3f}s")
        elif status_code >= 400:
            log_level = logging.WARNING
            logger.warning(f"{method} {url} completed with status {status_code} in {response_time:.3f}s")
        else:
            log_level = logging.INFO
            logger.info(f"{method} {url} completed with status {status_code} in {response_time:.3f}s")
    except Exception as e:
        # Fallback logging if something goes wrong
        logger.error(f"Error logging request details: {str(e)}")


# Create default application logger
logger = setup_logger()


def get_task_logger(task_name: str) -> logging.Logger:
    """
    Get a logger specifically for Celery tasks.
    
    Args:
        task_name: The name of the task
        
    Returns:
        logging.Logger: Configured logger for the task
    """
    return setup_logger(f"celery.task.{task_name}")


# Make these functions available for import
__all__ = ['setup_logger', 'logger', 'get_task_logger', 'log_request_details']