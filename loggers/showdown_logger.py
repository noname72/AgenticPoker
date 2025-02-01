import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class ShowdownLogger:
    """Handles all logging operations for showdown-related actions."""

    @staticmethod
    def log_showdown_start() -> None:
        """Log the start of showdown phase."""
        logger.info("\n=== Showdown ===")

    @staticmethod
    def log_player_hand(player_name: str, hand_description: str) -> None:
        """Log a player's hand at showdown."""
        logger.info(f"{player_name} shows: {hand_description}")

    @staticmethod
    def log_single_winner(winner_name: str, amount: int) -> None:
        """Log when there's a single winner (others folded)."""
        logger.info(f"{winner_name} wins ${amount} (all others folded)")

    @staticmethod
    def log_pot_win(winner_name: str, amount: int, is_split: bool = False) -> None:
        """Log when a player wins a pot."""
        action = "splits" if is_split else "wins"
        logger.info(f"{winner_name} {action} ${amount}")

    @staticmethod
    def log_side_pot_distribution(
        pot_number: int, amount: int, eligible_players: List[str]
    ) -> None:
        """Log the distribution of a side pot."""
        players_str = ", ".join(eligible_players)
        logger.info(f"\nSide pot {pot_number} (${amount}) - Eligible: {players_str}")

    @staticmethod
    def log_hand_comparison(
        winner_name: str,
        loser_name: str,
        comparison: int,
        winner_hand: str,
        loser_hand: str,
    ) -> None:
        """Log a clear comparison between two players' hands."""
        # If comparison > 0, first hand wins
        # If comparison == 0, it's a tie
        # If comparison < 0, second hand wins
        result = (
            "loses to"
            if comparison > 0  # First hand loses to second hand
            else (
                "ties with" if comparison == 0 else "beats"
            )  # First hand beats second hand
        )
        logger.info(
            f"{winner_name}'s {winner_hand} {result} {loser_name}'s {loser_hand}"
        )

    @staticmethod
    def log_evaluation_error(error: Exception) -> None:
        """Log errors during hand evaluation."""
        logger.error(f"Error evaluating hands: {str(error)}")

    @staticmethod
    def log_chip_movements(
        player_name: str, initial_chips: int, final_chips: int
    ) -> None:
        """Log chip movements for a player."""
        difference = final_chips - initial_chips
        direction = "gains" if difference > 0 else "loses"
        amount = abs(difference)
        logger.info(
            f"{player_name} {direction} ${amount} "
            f"(${initial_chips} -> ${final_chips})"
        )

    @staticmethod
    def log_hand_evaluation(
        player_name: str,
        cards: List[str],
        description: str,
        rank: int,
        tiebreakers: List[int],
    ) -> None:
        """Log detailed hand evaluation information."""
        logger.info(f"{player_name}'s hand evaluation:")
        logger.info(f"  Cards: {', '.join(cards)}")
        logger.info(f"  Hand: {description}")
        logger.info(f"  Rank: {rank}")
        logger.info(f"  Tiebreakers: {tiebreakers}")

    @staticmethod
    def log_pot_award(winner_name: str, pot_amount: int) -> None:
        """Log pot being awarded to winner."""
        logger.info(f"{winner_name} wins pot of ${pot_amount}")
