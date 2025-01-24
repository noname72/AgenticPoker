import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DrawLogger:
    """Handles all logging operations for draw-related actions."""

    @staticmethod
    def log_preemptive_reshuffle(
        needed: int, available: Optional[int] = None, skip: bool = False
    ) -> None:
        """Log preemptive reshuffle status."""
        if skip:
            logger.info(
                f"Pre-emptive reshuffle skipped - have exact number of cards needed ({needed})"
            )
        else:
            logger.info(
                f"Pre-emptive reshuffle: Need up to {needed} cards, "
                f"only {available} remaining"
            )

    @staticmethod
    def log_discard_validation_error(player_name: str, discard_count: int) -> None:
        """Log when a player tries to discard too many cards."""
        logger.warning(
            f"{player_name} tried to discard {discard_count} cards. Maximum is 5."
        )

    @staticmethod
    def log_invalid_indexes(player_name: str) -> None:
        """Log when a player provides invalid discard indexes."""
        logger.warning(f"{player_name} invalid discard indexes")
        logger.info(f"{player_name} keeping current hand")

    @staticmethod
    def log_draw_error(player_name: str, error: Exception) -> None:
        """Log errors during draw phase."""
        logger.error(f"Error in draw phase for {player_name}: {error}")

    @staticmethod
    def log_non_ai_player(player_name: str) -> None:
        """Log when a non-AI player is encountered."""
        logger.info(
            f"{player_name} is a non-AI player or player without decision method; keeping current hand"
        )

    @staticmethod
    def log_discard_action(player_name: str, count: int) -> None:
        """Log player discard action."""
        logger.info(f"Draw phase: {player_name} discarding {count} cards")

    @staticmethod
    def log_reshuffle_status(needed: int, available: int, skip: bool = False) -> None:
        """Log reshuffle status during draw."""
        if skip:
            logger.info(
                f"Reshuffle skipped - have exact number of cards needed ({needed})"
            )
        else:
            logger.info(
                f"Deck low on cards ({available} remaining). "
                f"Need {needed} cards. Reshuffling..."
            )

    @staticmethod
    def log_deck_status(player_name: str, remaining: int) -> None:
        """Log deck status after player's draw."""
        logger.info(
            f"Deck status after {player_name}'s draw: {remaining} cards remaining"
        )

    @staticmethod
    def log_keep_hand(player_name: str, explicit_decision: bool = False) -> None:
        """Log when a player keeps their current hand."""
        if explicit_decision:
            logger.info(f"{player_name} keeping current hand (explicit decision)")
        else:
            logger.info(f"{player_name} keeping current hand")
