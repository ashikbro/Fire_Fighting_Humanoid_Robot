"""
Enhanced error handling and logging module
"""
import logging
import traceback
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
from functools import wraps

# Create logs directory if it doesn't exist
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better visibility"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'ENDC': '\033[0m'       # End color
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['ENDC'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['ENDC']}"
        return super().format(record)

def setup_logging(log_level: str = "INFO", log_file: str = None) -> logging.Logger:
    """Setup enhanced logging configuration"""
    
    # Create logger
    logger = logging.getLogger("firebot")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file is None:
        log_file = os.path.join(LOG_DIR, f"firebot_{datetime.now().strftime('%Y%m%d')}.log")
    
    file_handler = logging.FileHandler(log_file)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler for errors and above
    error_file = os.path.join(LOG_DIR, f"firebot_errors_{datetime.now().strftime('%Y%m%d')}.log")
    error_handler = logging.FileHandler(error_file)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    return logger

def log_exception(logger: logging.Logger, exception: Exception, context: str = None):
    """Log exception with full traceback and context"""
    error_msg = f"Exception in {context}: {str(exception)}" if context else f"Exception: {str(exception)}"
    logger.error(error_msg)
    logger.error(f"Traceback: {traceback.format_exc()}")

def safe_execute(func, logger: logging.Logger, default_return=None, context: str = None):
    """Safely execute a function with error logging"""
    try:
        return func()
    except Exception as e:
        log_exception(logger, e, context or func.__name__)
        return default_return

def error_handler(logger: logging.Logger = None, reraise: bool = False, default_return=None):
    """Decorator for automatic error handling"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if logger:
                    log_exception(logger, e, func.__name__)
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator

class RobotException(Exception):
    """Base exception for robot-related errors"""
    def __init__(self, message: str, error_code: str = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.timestamp = datetime.now()

class VisionException(RobotException):
    """Exception for vision/detection related errors"""
    pass

class NavigationException(RobotException):
    """Exception for navigation related errors"""
    pass

class SensorException(RobotException):
    """Exception for sensor related errors"""
    pass

class CommunicationException(RobotException):
    """Exception for communication related errors"""
    pass

# Global logger instance
logger = setup_logging()

# Export commonly used items
__all__ = [
    'setup_logging', 'log_exception', 'safe_execute', 'error_handler',
    'RobotException', 'VisionException', 'NavigationException', 
    'SensorException', 'CommunicationException', 'logger'
]
