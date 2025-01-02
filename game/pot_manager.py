import logging
from typing import Dict, List, Optional

from exceptions import InvalidGameStateError

from .player import Player
from .types import SidePot, SidePotView


class PotManager:
    """
    Manages poker game pot and side pot calculations.

    This class handles all pot-related operations including tracking the main pot,
    calculating side pots when players go all-in, and providing formatted views
    of the pot state for logging and display.

    The PotManager maintains consistency of all chip movements and ensures that:
    - Total chips in play remain constant
    - Side pots are correctly calculated for all-in situations
    - Pot state can be validated at any time
    - Chip movements are properly logged for debugging

    Attributes:
        pot (int): Current amount in the main pot
        side_pots (Optional[List[SidePot]]): List of active side pots, if any.
            None indicates no side pots have been calculated yet.
            Empty list indicates calculation returned no side pots.

    Usage:
        pot_manager = PotManager()

        # Add chips to main pot
        pot_manager.add_to_pot(100)

        # Calculate side pots when players go all-in
        side_pots = pot_manager.calculate_side_pots(active_players)

        # Get formatted view of side pots
        pot_view = pot_manager.get_side_pots_view()

        # Reset at end of hand
        pot_manager.reset_pot()

    Note:
        - Side pots are only created when players go all-in for different amounts
        - Main pot and side pots are kept separate for proper pot distribution
        - All chip movements are logged for debugging and validation
        - Pot state can be restored from saved game state using set_pots()
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

        # Log pot changes for debugging
        old_pot = self.pot
        self.pot += amount
        logging.debug(f"Pot change: {old_pot} -> {self.pot} (+{amount})")

    def reset_pot(self) -> None:
        """
        Reset the pot manager state.

        Clears both the main pot and any side pots. Should only be called
        at the end of a hand when chips are being distributed to winners.

        Side Effects:
            - Sets main pot to 0
            - Clears all side pots
        """
        # Log pot reset for debugging
        old_pot = self.pot
        old_side_pots = self.side_pots

        self.pot = 0
        self.side_pots = None

        logging.debug(
            f"Pot reset: Main {old_pot}->0, " f"Side pots {old_side_pots}->None"
        )

    def calculate_side_pots(self, active_players: List[Player]) -> List[SidePot]:
        """
        Calculate side pots when one or more players is all-in.

        Args:
            active_players (List[Player]): List of all players still in the hand,
                                         including those who are all-in or folded

        Returns:
            List[SidePot]: List of calculated side pots, where each pot contains
                          an amount and list of eligible players

        Side Effects:
            - Updates self.side_pots with the calculated side pots
            - Sets self.side_pots to empty list if no active players

        Note:
            This method assumes that any existing main pot (self.pot) should be
            preserved and included in chip total validation. If you need to reset
            the main pot before calculation, call reset_pot() first.

        Edge Cases:
            - Empty input: Returns empty list and sets self.side_pots to []
            - All players folded: Creates pots with no eligible players
            - Single chip differences: Creates separate pots for each bet level
            - Existing main pot: Preserves main pot and only calculates side pots for new bets
        """
        # Validate inputs
        if not active_players:
            self.side_pots = []
            return []

        # Track total chips in play before calculation (including folded players and main pot)
        total_chips_before = sum(p.chips + p.bet for p in active_players) + self.pot

        # Create dictionary of all bets, including folded players' bets
        posted_amounts = {
            p: p.bet
            for p in active_players
            if p.bet > 0  # Include folded players' bets
        }
        if not posted_amounts:
            return []

        # Calculate side pots
        side_pots = []
        current_amount = 0

        # Sort players by their bet amounts
        sorted_players = sorted(posted_amounts.items(), key=lambda x: x[1])

        # Track processed amounts to avoid double counting
        processed_amounts = {}

        for player, amount in sorted_players:
            if amount > current_amount:
                # Find all eligible players (not folded and bet >= amount)
                eligible = [
                    p
                    for p, bet in posted_amounts.items()
                    if bet >= amount and not p.folded
                ]

                # Calculate contribution from each player for this level
                contribution = amount - current_amount

                # Calculate number of contributors at this level
                contributors = sum(
                    1 for bet in posted_amounts.values() if bet >= amount
                )

                # Calculate pot size for this level
                pot_size = contribution * contributors

                # Only create a new side pot if it would have a positive amount
                # and hasn't been processed at this level
                if pot_size > 0 and amount not in processed_amounts:
                    # Check if we can combine with the previous pot
                    if side_pots and set(side_pots[-1].eligible_players) == set(
                        eligible
                    ):
                        # Create new pot with combined amount
                        combined_pot = SidePot(
                            amount=side_pots[-1].amount + pot_size,
                            eligible_players=eligible,
                        )
                        side_pots[-1] = combined_pot
                    else:
                        side_pots.append(SidePot(pot_size, eligible))
                    processed_amounts[amount] = pot_size

                current_amount = amount

        # Validate total chips haven't changed (including main pot)
        total_chips_after = (
            sum(p.chips for p in active_players)
            + self.pot
            + sum(pot.amount for pot in side_pots)
        )

        if total_chips_before != total_chips_after:
            raise InvalidGameStateError(
                f"Chip total mismatch in side pot calculation: {total_chips_before} vs {total_chips_after}"
            )

        # Store the calculated side pots
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

    def set_pots(
        self, main_pot: int, side_pots: Optional[List[SidePot]] = None
    ) -> None:
        """
        Set the main pot and side pots directly.

        Args:
            main_pot: Amount for the main pot (must be non-negative)
            side_pots: Optional list of side pots to set

        Raises:
            ValueError: If main_pot is negative

        Side Effects:
            - Updates the main pot amount
            - Updates the side pots list
            - Logs the changes for debugging

        Note:
            This method is typically used for:
            - Initializing pot state at the start of a hand
            - Restoring pot state from saved game
            - Testing pot scenarios
        """
        if main_pot < 0:
            raise ValueError("Main pot cannot be negative")

        # Log pot changes for debugging
        old_pot = self.pot
        old_side_pots = self.side_pots

        self.pot = main_pot
        self.side_pots = side_pots

        logging.debug(
            f"Pot update: Main {old_pot}->{main_pot}, "
            f"Side pots {old_side_pots}->{side_pots}"
        )

    def validate_pot_state(
        self, active_players: List[Player], initial_total: Optional[int] = None
    ) -> bool:
        """
        Validate the current pot state for consistency.

        Checks that:
        1. Total chips in play (including pots) matches initial total if provided
        2. Current bets don't exceed pot amounts
        3. All chip movements are accounted for

        Args:
            active_players: List of players still in the hand
            initial_total: Optional initial total chips to validate against

        Returns:
            bool: True if pot state is valid

        Raises:
            InvalidGameStateError: If pot state is invalid, with detailed error message

        Side Effects:
            None - This is a validation method only

        Note:
            When validating with initial_total, includes:
            - Chips in player stacks
            - Current bets
            - Main pot
            - All side pots
        """
        # Calculate total chips in play (excluding bets since they're in the pot)
        total_chips = sum(p.chips for p in active_players)

        # Calculate total in pots
        total_in_pots = self.pot
        if self.side_pots:
            total_in_pots += sum(pot.amount for pot in self.side_pots)

        # Calculate total bets in current round
        total_bets = sum(p.bet for p in active_players)

        # For pot validation, we only care about current round's bets
        # The pot should be at least equal to current bets
        if total_bets > total_in_pots:
            logging.error(
                f"Pot mismatch - Total bets: {total_bets}, Total in pots: {total_in_pots}"
            )
            logging.error(f"Main pot: {self.pot}")
            if self.side_pots:
                logging.error(
                    f"Side pots: {[(pot.amount, [p.name for p in pot.eligible_players]) for pot in self.side_pots]}"
                )
            logging.error(
                f"Active players: {[(p.name, p.chips, p.bet) for p in active_players]}"
            )
            raise InvalidGameStateError(
                f"Current bets exceed pot: bets={total_bets}, pots={total_in_pots}"
            )

        # If initial total provided, validate total chips haven't changed
        if initial_total is not None:
            # Current total is chips in players' stacks plus all pots
            # Note: Don't add bets since they're already counted in the pot
            current_total = total_chips + total_in_pots
            if current_total != initial_total:
                logging.error(
                    f"Total chips mismatch - Initial: {initial_total}, Current: {current_total}"
                )
                logging.error(
                    f"Player chips: {[(p.name, p.chips) for p in active_players]}"
                )
                logging.error(f"Pots: Main={self.pot}, Side={self.side_pots}")
                logging.error(
                    f"Current bets: {[(p.name, p.bet) for p in active_players]}"
                )
                raise InvalidGameStateError(
                    f"Total chips changed: initial={initial_total}, current={current_total}"
                )

        return True

    def end_betting_round(self, active_players: List[Player]) -> None:
        """
        Handle the end of a betting round.

        Args:
            active_players: List of players still in the hand

        Side Effects:
            - Updates pot amount with current bets
            - Clears player bet amounts
        """
        # Add current bets to pot
        total_bets = sum(p.bet for p in active_players)
        self.add_to_pot(total_bets)

        # Clear player bets
        for player in active_players:
            player.bet = 0

        # Log for debugging
        logging.debug(f"End of betting round - New pot total: {self.pot}")
