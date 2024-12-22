import logging
import sys
from datetime import datetime


def setup_logging(session_id=0):
    """
    Configure logging with UTF-8 encoding support and session management.

    Args:
        session_id (str, optional): Unique identifier for this game session.
            If None, generates timestamp-based ID.

    Side Effects:
        - Configures root logger
        - Creates new log file for session
        - Sets up console output
    """
    # Clear any existing handlers
    logging.getLogger().handlers = []

    # Generate session ID if not provided
    if not session_id:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create log filename with session ID
    log_filename = f"poker_game.log"

    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            # Console handler with UTF-8 encoding
            logging.StreamHandler(sys.stdout),
            # File handler with UTF-8 encoding and session-specific file
            logging.FileHandler(log_filename, encoding="utf-8", mode="w"),
        ],
    )

    # Silence httpx logging
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Log session start with clear separator
    logging.info(f"\n{'='*70}")
    logging.info(f"New Poker Game Session Started - ID: {session_id}")
    logging.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"{'='*70}\n")
