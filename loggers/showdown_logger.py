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
    def log_player_hand(player_name: str, hand: str) -> None:
        """Log a player's hand at showdown."""
        logger.info(f"{player_name}'s hand: {hand}")

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
        player_name: str, hand: str, hand_rank: Optional[str] = None
    ) -> None:
        """Log details of hand comparison."""
        if hand_rank:
            logger.debug(f"{player_name}'s hand: {hand} ({hand_rank})")
        else:
            logger.debug(f"{player_name}'s hand: {hand}")

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
    def log_hand_evaluation(player_name: str, cards: List[str], description: str, rank: int, tiebreakers: List[int]) -> None:
        """Log detailed hand evaluation information."""
        logger.info(f"{player_name}'s hand evaluation:")
        logger.info(f"  Cards: {', '.join(cards)}")
        logger.info(f"  Hand: {description}")
        logger.info(f"  Rank: {rank}")
        logger.info(f"  Tiebreakers: {tiebreakers}")

    @staticmethod
    def log_hand_comparison(player1_name: str, player2_name: str, comparison_result: int, hand1_desc: str = None, hand2_desc: str = None) -> None:
        """Log hand comparison results with hand descriptions."""
        result_text = "better than" if comparison_result > 0 else "worse than" if comparison_result < 0 else "equal to"
        logger.info(f"{player1_name}'s hand is {result_text} {player2_name}'s hand")
        
        if comparison_result != 0:
            if comparison_result > 0:
                winner, loser = player1_name, player2_name
                winner_hand, loser_hand = hand1_desc, hand2_desc
            else:
                winner, loser = player2_name, player1_name
                winner_hand, loser_hand = hand2_desc, hand1_desc
            
            if winner_hand and loser_hand:
                logger.info(f"  ({winner} wins with {winner_hand} vs {loser}'s {loser_hand})")
            else:
                logger.info(f"  ({winner} wins the comparison)")
