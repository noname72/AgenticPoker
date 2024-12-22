import logging
import sys


def setup_logging():
    """
    Configure logging with UTF-8 encoding support for emoji characters.

    Sets up logging to both console and file with proper encoding handling:
    - Console output uses UTF-8 encoding
    - File output uses UTF-8 encoding
    - Logging level set to INFO
    """
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            # Console handler with UTF-8 encoding
            logging.StreamHandler(sys.stdout),
            # File handler with UTF-8 encoding
            logging.FileHandler("poker_game.log", encoding="utf-8"),
        ],
    )

    # Silence httpx logging
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Log initial message
    logging.info("=== New Poker Game Session Started ===")
