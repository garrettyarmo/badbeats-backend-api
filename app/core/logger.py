import logging
import sys
from typing import Optional

class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages based on level"""
    
    COLORS = {
        logging.DEBUG: '\033[36m',    # Cyan
        logging.INFO: '\033[32m',     # Green
        logging.WARNING: '\033[33m',   # Yellow
        logging.ERROR: '\033[31m',     # Red
        logging.CRITICAL: '\033[41m',  # Red background
    }
    
    RESET = '\033[0m'
    
    def format(self, record):
        # Add color codes before the message
        color = self.COLORS.get(record.levelno, self.RESET)
        record.msg = f"{color}{record.msg}{self.RESET}"
        return super().format(record)

def setup_logger(name: str = "app", level: Optional[str] = "INFO") -> logging.Logger:
    """
    Set up and configure a logger with colored output
    
    Args:
        name: The name of the logger
        level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Set logging level
    level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add formatter to handler
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    if not logger.handlers:
        logger.addHandler(console_handler)
    
    return logger

# Create default logger instance
logger = setup_logger()
