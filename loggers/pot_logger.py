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
