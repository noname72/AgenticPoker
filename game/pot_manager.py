from typing import Dict, List, Optional
import logging

from exceptions import InvalidGameStateError

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

    def calculate_side_pots(self, active_players: List[Player], all_in_players: List[Player]) -> List[SidePot]:
        """
        Calculate side pots when one or more players is all-in.
        
        Args:
            active_players: List of players still in the hand
            all_in_players: List of players who have gone all-in
        
        Returns:
            List of SidePot objects, each containing amount and eligible players
            
        Raises:
            InvalidGameStateError: If chip totals don't match before and after calculation
        """
        # Validate inputs
        if not active_players:
            return []
        
        # Track total chips in play before calculation
        total_chips_before = sum(p.chips for p in active_players) + sum(p.bet for p in active_players)
        
        # Create dictionary of all bets
        posted_amounts = {p: p.bet for p in active_players if p.bet > 0}
        
        # Calculate side pots
        side_pots = []
        current_amount = 0
        
        # Sort players by their bet amounts
        sorted_players = sorted(posted_amounts.items(), key=lambda x: x[1])
        
        for player, amount in sorted_players:
            if amount > current_amount:
                # Find all players who bet this much or more
                eligible = [p for p, bet in posted_amounts.items() if bet >= amount]
                
                # Calculate pot size for this level
                pot_size = (amount - current_amount) * len(eligible)
                
                if pot_size > 0:
                    side_pots.append(SidePot(pot_size, eligible))
                
                current_amount = amount
        
        # Validate total chips haven't changed
        total_chips_after = (
            sum(p.chips for p in active_players) + 
            sum(pot.amount for pot in side_pots)
        )
        
        if total_chips_before != total_chips_after:
            raise InvalidGameStateError(
                f"Chip total mismatch in side pot calculation: {total_chips_before} vs {total_chips_after}"
            )
        
        # Log side pots for debugging
        if side_pots:
            logging.info("\nCalculated side pots:")
            for i, pot in enumerate(side_pots, 1):
                players_str = ", ".join(p.name for p in pot.eligible_players)
                logging.info(f"  Pot {i}: ${pot.amount} (Eligible: {players_str})")
        
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
