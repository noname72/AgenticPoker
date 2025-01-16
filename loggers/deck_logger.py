import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DeckLogger:
    """Handles all logging operations for deck-related actions."""

    @staticmethod
    def log_shuffle(remaining_cards: Optional[int] = None) -> None:
        """Log deck shuffling."""
        if remaining_cards is not None and remaining_cards != 52:
            logger.info(f"Shuffling deck with {remaining_cards} cards")

    @staticmethod
    def log_reshuffle() -> None:
        """Log full deck reshuffle."""
        logger.info("Full deck reshuffle - all 52 cards back in play")

    @staticmethod
    def log_deal_error(requested: int, available: int) -> None:
        """Log error when trying to deal too many cards."""
        logger.error(
            f"Cannot deal {requested} cards. Only {available} cards remaining."
        )
