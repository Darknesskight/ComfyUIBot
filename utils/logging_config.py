"""
Simple centralized logging configuration for ComfyUI Discord Bot.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

# Simple log directory
LOG_DIR = "logs"
Path(LOG_DIR).mkdir(exist_ok=True)

def setup_logging(log_level=None):
    """Set up basic logging with daily rotation."""
    
    # Get log level from environment variable, fallback to INFO if not set
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Simple format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with daily rotation
    file_handler = logging.handlers.TimedRotatingFileHandler(
        os.path.join(LOG_DIR, "bot.log"),
        when='midnight',
        interval=1,
        backupCount=7,  # Keep 7 days of logs
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    return root_logger

def get_logger(name):
    """Get a logger for a module."""
    return logging.getLogger(name)
