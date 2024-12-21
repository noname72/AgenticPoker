import logging
import os


def setup_logging():
    """Configure application-wide logging with file cleanup."""
    # Clear existing handlers to avoid duplicate logging
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Clear the log file
    log_file = "poker_game.log"
    if os.path.exists(log_file):
        with open(log_file, "w") as f:
            f.write("")  # Clear the file

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")

    # Create and configure file handler
    file_handler = logging.FileHandler(
        filename=log_file,
        mode="w",  # Use write mode to start fresh each time
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Log initial message to confirm setup
    root_logger.info("=== New Poker Game Session Started ===")
