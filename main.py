import logging
from logging.handlers import RotatingFileHandler

from poker_game import PokerGame

def setup_logging():
    """Configure application-wide logging."""
    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )

    # Create and configure file handler with rotation
    file_handler = RotatingFileHandler(
        filename="poker_game.log",
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5,
        mode="a",  # Append mode instead of overwrite
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

if __name__ == "__main__":
    setup_logging()
    game = PokerGame()
    game.play_round()
