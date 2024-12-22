import json
import logging
import os
from pathlib import Path


def setup_logging():
    """Configure logging for the poker game."""
    # Clear existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure formatters
    console_formatter = logging.Formatter("%(message)s")
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler - only show game info
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # File handler - include debug but filter out httpx
    file_handler = logging.FileHandler("poker_game.log", mode="w")
    file_handler.setLevel(logging.INFO)  # Change to INFO to reduce noise
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Silence httpx logging
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Log initial message
    root_logger.info("=== New Poker Game Session Started ===")
