from typing import Dict, List, Optional

from .player import Player
from .types import SidePot, SidePotView


class PotManager:
    """
    Manages poker game pot and side pot calculations.

    This class handles all pot-related operations including tracking the main pot,
    calculating side pots when players go all-in, and providing formatted views
    of the pot state for logging and display.

    Attributes:
        pot (int): Current amount in the main pot
        side_pots (Optional[List[SidePot]]): List of active side pots, if any
    """

    def __init__(self) -> None:
        """Initialize a new pot manager with empty pot and no side pots."""
        self.pot: int = 0
        self.side_pots: Optional[List[SidePot]] = None

    def add_to_pot(self, amount: int) -> None:
        """
        Add chips to the main pot.

        Args:
            amount (int): Amount of chips to add to the pot. Must be non-negative.

        Raises:
            ValueError: If amount is negative

        Side Effects:
            - Increases the main pot by the specified amount
        """
        if amount < 0:
            raise ValueError("Cannot add negative amount to pot")
        self.pot += amount

    def reset_pot(self) -> None:
        """
        Reset the pot manager state.

        Clears both the main pot and any side pots. Typically called at the
        end of a hand or when starting a new round.

        Side Effects:
            - Sets main pot to 0
            - Clears all side pots
        """
        self.pot = 0
        self.side_pots = None

    def calculate_side_pots(self, posted_amounts: Dict[Player, int]) -> List[SidePot]:
        """
        Calculate side pots based on player bets.

        Creates side pots when players have gone all-in with different amounts.
        Each side pot tracks its amount and eligible players.

        Args:
            posted_amounts: Dictionary mapping players to their total bet amounts

        Returns:
            List of SidePot objects, each containing a pot amount and list of
            eligible players

        Side Effects:
            - Updates self.side_pots with the calculated side pots

        Example:
            >>> posted_amounts = {
            ...     player_a: 100,  # all-in
            ...     player_b: 200,  # all-in
            ...     player_c: 300   # active
            ... }
            >>> side_pots = pot_manager.calculate_side_pots(posted_amounts)
            # Returns: [
            #   SidePot(300, [player_a, player_b, player_c]),
            #   SidePot(300, [player_b, player_c]),
            #   SidePot(300, [player_c])
            # ]
        """
        side_pots = []
        sorted_players = sorted(posted_amounts.items(), key=lambda x: x[1])
        current_amount = 0
        for player, amount in sorted_players:
            if amount > current_amount:
                eligible = [p for p, a in posted_amounts.items() if a >= amount]
                pot_size = (amount - current_amount) * len(eligible)
                if pot_size > 0:
                    side_pots.append(SidePot(pot_size, eligible))
                current_amount = amount
        self.side_pots = side_pots
        return side_pots

    def get_side_pots_view(self) -> List[SidePotView]:
        """
        Get a display-friendly view of the current side pots.
        """
        if not self.side_pots:
            return []
        return [
            {
                "amount": pot.amount,
                "eligible_players": [p.name for p in pot.eligible_players],
            }
            for pot in self.side_pots
        ]

    def log_side_pots(self, logger) -> None:
        """
        Log the current side pot state.
        """
        if not self.side_pots:
            return
        logger.info("\nSide pots:")
        for i, pot in enumerate(self.get_side_pots_view(), 1):
            players_str = ", ".join(pot["eligible_players"])
            logger.info(f"  Pot {i}: ${pot['amount']} (Eligible: {players_str})")
