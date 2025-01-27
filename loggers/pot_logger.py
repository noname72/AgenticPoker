import logging
from typing import Any, Dict, List, Optional

from data.types.pot_types import SidePot

logger = logging.getLogger(__name__)


class PotLogger:
    """Handles all logging operations for pot-related actions."""

    @staticmethod
    def log_pot_change(old_pot: int, new_pot: int, amount: int) -> None:
        """Log changes to the pot amount."""
        logger.debug(f"Pot change: {old_pot} -> {new_pot} (+{amount})")

    @staticmethod
    def log_pot_reset(old_pot: int, old_side_pots: Optional[List[SidePot]]) -> None:
        """Log pot reset operations."""
        logger.debug(f"Pot reset: Main {old_pot}->0, Side pots {old_side_pots}->None")

    @staticmethod
    def log_new_side_pot(amount: int, eligible: List[str]) -> None:
        """Log creation of a new side pot."""
        logger.debug(f"Created new pot: amount={amount}, eligible={eligible}")

    @staticmethod
    def log_chip_mismatch(
        initial: int,
        current: int,
        players: List[Dict[str, Any]],
        pots: Dict[str, Any],
        bets: List[Dict[str, Any]],
    ) -> None:
        """Log chip total mismatch errors."""
        logger.error(f"Total chips mismatch - Initial: {initial}, Current: {current}")
        logger.error(f"Player chips: {players}")
        logger.error(f"Pots: Main={pots['main']}, Side={pots['side']}")
        logger.error(f"Current bets: {bets}")

    @staticmethod
    def log_pot_update(
        old_pot: int,
        new_pot: int,
        old_side_pots: Optional[List[SidePot]],
        new_side_pots: Optional[List[SidePot]],
    ) -> None:
        """Log pot state updates."""
        logger.debug(
            f"Pot update: Main {old_pot}->{new_pot}, "
            f"Side pots {old_side_pots}->{new_side_pots}"
        )

    @staticmethod
    def log_betting_round_end(new_pot: int) -> None:
        """Log end of betting round."""
        logger.debug(f"End of betting round - New pot total: {new_pot}")

    @staticmethod
    def log_side_pots_info(side_pots: List[SidePot]) -> None:
        """Log detailed side pot information."""
        logger.info("\nSide pots:")
        for i, pot in enumerate(side_pots, 1):
            players_str = ", ".join(pot.eligible_players)
            logger.info(f"  Pot {i}: ${pot.amount} (Eligible: {players_str})")

    @staticmethod
    def log_pot_validation_error(
        total_bets: int,
        total_in_pots: int,
        main_pot: int,
        side_pots: Optional[List[SidePot]],
        active_players: List[Dict[str, Any]],
    ) -> None:
        """Log pot validation errors."""
        logger.error(
            f"Pot mismatch - Total bets: {total_bets}, Total in pots: {total_in_pots}"
        )
        logger.error(f"Main pot: {main_pot}")
        if side_pots:
            logger.error(
                f"Side pots: {[(pot.amount, pot.eligible_players) for pot in side_pots]}"
            )
        logger.error(f"Active players: {active_players}")

    @staticmethod
    def log_pot_merge(amount: int, eligible_players: List[str]) -> None:
        """Log when side pots with identical eligible players are merged.

        Args:
            amount: Amount being merged into existing pot
            eligible_players: List of players eligible for the merged pot
        """
        players_str = ", ".join(eligible_players)
        logger.debug(
            f"Merging pot: ${amount} into existing pot with eligible players: {players_str}"
        )

    @staticmethod
    def log_pot_validation_info(message: str) -> None:
        """Log informational messages during pot validation.

        Args:
            message: The validation message to log
        """
        logger.debug(f"Pot validation: {message}")

    @staticmethod
    def log_bet_cleared(player_name: str, old_bet: int) -> None:
        """Log when a player's bet is cleared and moved to pot.

        Args:
            player_name: Name of the player whose bet was cleared
            old_bet: Amount of bet that was cleared
        """
        logger.debug(f"Cleared {player_name}'s bet of ${old_bet}")

    @staticmethod
    def log_betting_round_start(initial_pot: int, total_bets: int) -> None:
        """Log the start of a betting round with initial state.

        Args:
            initial_pot: Amount in main pot before betting
            total_bets: Total amount of current bets
        """
        logger.debug(
            f"Starting betting round - Main pot: ${initial_pot}, "
            f"Current bets: ${total_bets}"
        )

    @staticmethod
    def log_pot_total(main_pot: int, current_bets: int) -> None:
        """Log the current total pot including bets.

        Args:
            main_pot: Amount in main pot
            current_bets: Total of current bets
        """
        total = main_pot + current_bets
        logger.debug(
            f"Current pot total: ${total} "
            f"(Main: ${main_pot} + Bets: ${current_bets})"
        )

    @staticmethod
    def log_bet_moved_to_pot(player_name: str, bet_amount: int, new_pot: int) -> None:
        """Log when a player's bet is moved to the pot.

        Args:
            player_name: Name of the player whose bet was moved
            bet_amount: Amount of bet moved to pot
            new_pot: New total pot amount after adding bet
        """
        logger.debug(
            f"Moving {player_name}'s bet of ${bet_amount} to pot. "
            f"New pot total: ${new_pot}"
        )
