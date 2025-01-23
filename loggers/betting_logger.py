import logging
from typing import List, Optional

from data.types.pot_types import SidePot

logger = logging.getLogger(__name__)


class BettingLogger:
    """Handles all logging operations for betting-related actions."""

    @staticmethod
    def log_player_turn(
        player_name: str,
        hand: str,
        chips: int,
        current_bet: int,
        pot: int,
        active_players: List[str],
        last_raiser: Optional[str] = None,
    ) -> None:
        """Log the start of a player's turn with all relevant information."""
        logger.info(f"---- {player_name} is active ----")
        logger.info(f"  Active players: {active_players}")
        logger.info(f"  Last raiser: {last_raiser if last_raiser else 'None'}")
        logger.info(f"  Hand: {hand}")
        logger.info(f"  Player chips: ${chips}")
        logger.info(f"  Player current bet: ${current_bet}")
        logger.info(f"  Current pot: ${pot}")

    @staticmethod
    def log_player_action(
        player_name: str,
        action: str,
        amount: int = 0,
        is_all_in: bool = False,
        pot: Optional[int] = None,
    ) -> None:
        """Log a player's betting action."""
        status = " (all in)" if is_all_in else ""

        if action == "fold":
            logger.info(f"{player_name} folds")
        elif action == "check":
            logger.info(f"{player_name} checks")
        elif action == "call":
            logger.info(f"{player_name} calls ${amount}{status}")
            if pot is not None:
                logger.info(f"  Pot after call: ${pot}")
        elif action == "raise":
            logger.info(f"{player_name} raises to ${amount}{status}")

        if pot is not None:
            logger.info(f"  Pot after action: ${pot}")

    @staticmethod
    def log_raise_limit(max_raises: int) -> None:
        """Log when max raises is reached."""
        logger.info(f"Max raises ({max_raises}) reached, converting raise to call")

    @staticmethod
    def log_invalid_raise(raise_amount: int, min_raise: int) -> None:
        """Log when a raise amount is invalid."""
        logger.info(
            f"Raise amount ${raise_amount} below minimum (${min_raise}), converting to call"
        )

    @staticmethod
    def log_showdown() -> None:
        """Log when a showdown situation occurs."""
        logger.info("Showdown situation: Only one player with chips remaining")

    @staticmethod
    def log_side_pots(side_pots: List[SidePot]) -> None:
        """Log created side pots."""
        logger.debug("Side pots created:")
        for i, pot in enumerate(side_pots, start=1):
            logger.debug(f"  Pot {i}: ${pot.amount} - Eligible: {pot.eligible_players}")

    @staticmethod
    def log_blind_or_ante(
        player_name: str,
        amount: int,
        actual_amount: int,
        is_ante: bool = False,
        is_small_blind: bool = False,
    ) -> None:
        """Log blind or ante postings."""
        action_type = (
            "ante" if is_ante else "small blind" if is_small_blind else "big blind"
        )
        status = " (all in)" if amount > actual_amount else ""

        if actual_amount < amount:
            logger.info(
                f"{player_name} posts partial {action_type} of ${actual_amount}{status}"
            )
        else:
            logger.info(
                f"{player_name} posts {action_type} of ${actual_amount}{status}"
            )

    @staticmethod
    def log_skip_player(player_name: str, reason: str) -> None:
        """Log when a player is skipped."""
        logger.info(f"{player_name} {reason}, skipping")

    @staticmethod
    def log_state_after_action(player_name: str, pot: int, chips: int) -> None:
        """Log game state after an action."""
        logger.info(f"  Pot after action: ${pot}")
        logger.info(f"  {player_name}'s remaining chips: ${chips}")
        logger.info("")

    @staticmethod
    def log_collecting_antes() -> None:
        """Log the start of ante collection."""
        logger.info("\nCollecting antes:")

    @staticmethod
    def log_line_break() -> None:
        """Log an empty line for formatting."""
        logger.info("")

    @staticmethod
    def log_message(message: str) -> None:
        """Log a general message."""
        logger.info(message)

    @staticmethod
    def log_debug(message: str) -> None:
        """Log a debug message."""
        logger.info(message)
