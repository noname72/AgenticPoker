import logging
from typing import Dict, Optional, Union

# Default log levels for each logger
DEFAULT_LOG_LEVELS = {
    "agent": logging.INFO,
    "betting": logging.INFO,
    "deck": logging.INFO,
    "draw": logging.INFO,
    "game": logging.INFO,
    "llm": logging.INFO,
    "memory": logging.INFO,
    "player": logging.INFO,
    "pot": logging.INFO,
    "showdown": logging.INFO,
    "strategy": logging.INFO,
    "table": logging.INFO,
}

def configure_loggers(log_levels: Optional[Dict[str, Union[int, str]]] = None) -> None:
    """Configure log levels for all loggers.
    
    Args:
        log_levels: Dictionary mapping logger names to their desired log levels.
                   Can use either logging constants (e.g. logging.INFO) 
                   or level names as strings (e.g. "INFO").
    """
    # Use default levels if none provided
    levels = log_levels or {}
    
    # Configure each logger
    for logger_name, default_level in DEFAULT_LOG_LEVELS.items():
        # Get the logger
        logger = logging.getLogger(f"loggers.{logger_name}_logger")
        
        # Set level from provided levels, falling back to default
        level = levels.get(logger_name, default_level)
        
        # Convert string level names to constants if needed
        if isinstance(level, str):
            level = getattr(logging, level.upper())
            
        logger.setLevel(level) 