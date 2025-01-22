import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class TableLogger:
    """Handles all logging operations for table-related actions and state changes."""

    @staticmethod
    def log_table_creation(num_players: int) -> None:
        """Log when a new table is created."""
        logger.info(f"New table created with {num_players} players")

    @staticmethod
    def log_dealer_position(position: int, player_name: str) -> None:
        """Log dealer button position."""
        logger.info(f"Dealer button at position {position} ({player_name})")

    @staticmethod
    def log_player_states(
        active: List[str], all_in: List[str], folded: List[str]
    ) -> None:
        """Log current state of all players at the table."""
        logger.debug("Table state:")
        logger.debug(f"  Active players: {', '.join(active)}")
        if all_in:
            logger.debug(f"  All-in players: {', '.join(all_in)}")
        if folded:
            logger.debug(f"  Folded players: {', '.join(folded)}")

    @staticmethod
    def log_next_player(
        player_name: str, position: int, needs_to_act: List[str]
    ) -> None:
        """Log when moving to next player in rotation."""
        logger.debug(
            f"Next to act: {player_name} (position {position})"
            f"\nStill to act: {', '.join(needs_to_act)}"
        )

    @staticmethod
    def log_round_complete(reason: str) -> None:
        """Log when a betting round is complete."""
        logger.info(f"Betting round complete: {reason}")

    @staticmethod
    def log_action_tracking_reset(
        active_players: List[str], street: Optional[str] = None
    ) -> None:
        """Log when action tracking is reset for a new betting round."""
        street_msg = f" for {street}" if street else ""
        logger.debug(
            f"Reset action tracking{street_msg}. "
            f"Active players: {', '.join(active_players)}"
        )

    @staticmethod
    def log_player_acted(
        player_name: str,
        is_raise: bool,
        needs_to_act: List[str],
        acted_since_raise: List[str],
    ) -> None:
        """Log when a player completes their action."""
        action_type = "raise" if is_raise else "action"
        logger.debug(
            f"{player_name} completed {action_type}"
            f"\nNeeds to act: {', '.join(needs_to_act)}"
            f"\nActed since last raise: {', '.join(acted_since_raise)}"
        )

    @staticmethod
    def log_table_state(
        active_count: int, all_in_count: int, folded_count: int
    ) -> None:
        """Log current table state counts."""
        logger.debug(
            f"Table state: {active_count} active, "
            f"{all_in_count} all-in, {folded_count} folded"
        )

    @staticmethod
    def log_skip_player(player_name: str, reason: str) -> None:
        """Log when a player is skipped in the rotation."""
        logger.debug(f"Skipping {player_name}: {reason}")

    @staticmethod
    def log_debug(message: str) -> None:
        """Log a debug message."""
        logger.debug(message)
