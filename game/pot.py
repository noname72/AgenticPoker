from typing import Any, Dict, List, Optional

from data.types.pot_types import PotState, SidePot
from exceptions import InvalidGameStateError
from game.player import Player
from loggers.pot_logger import PotLogger


class Pot:
    """
    Manages poker game pot and side pot calculations.

    This class handles all pot-related operations including tracking the main pot,
    calculating side pots when players go all-in, and providing formatted views
    of the pot state for logging and display.

    The Pot maintains consistency of all chip movements and ensures that:
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
        pot = Pot()

        # Add chips to main pot
        pot.add_to_pot(100)

        # Calculate side pots when players go all-in
        side_pots = pot.calculate_side_pots(active_players)

        # Get formatted view of side pots
        pot_view = pot.get_side_pots_view()

        # Reset at end of hand
        pot.reset_pot()

    Note:
        - Side pots are only created when players go all-in for different amounts
        - Main pot and side pots are kept separate for proper pot distribution
        - All chip movements are logged for debugging and validation
        - Pot state can be restored from saved game state using set_pots()
    """

    def __init__(self) -> None:
        """Initialize a new pot instance with empty pot and no side pots."""
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
        PotLogger.log_pot_change(old_pot, self.pot, amount)

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

        PotLogger.log_pot_reset(old_pot, old_side_pots)

    def calculate_side_pots(self, active_players: List[Player]) -> List[SidePot]:
        """
        Calculate side pots when one or more players is all-in.

        This method should be called BEFORE end_betting_round, while player.bet values
        are still set. The method calculates pot distributions but does not modify
        player bets - that's handled by end_betting_round.

        Args:
            active_players (List[Player]): List of ALL players who were dealt into the hand,
                including:
                - Players who are still in the hand
                - Players who folded but contributed chips
                - Players who are all-in
                Does NOT include players who mucked their hands without contributing.

        Returns:
            List[SidePot]: List of calculated side pots, where each pot contains
                          an amount and list of eligible players

        Side Effects:
            - Updates self.side_pots with the calculated side pots
            - Sets self.side_pots to empty list if no active players
            - Does NOT modify player.bet values - that's handled by end_betting_round

        Note:
            - Must be called before end_betting_round while bets are still set
            - Players who folded after betting are included in pot creation but not eligible
            - All-in players are eligible for pots up to their contribution amount
            - Side pots with identical eligible players are merged
        """
        # Validate inputs
        if not active_players:
            self.side_pots = []
            return []

        # Track total chips in play before calculation
        total_chips_before = (
            sum(p.chips + p.bet for p in active_players)  # Current chips + bets
            + self.pot  # Main pot
            + (
                sum(pot.amount for pot in self.side_pots) if self.side_pots else 0
            )  # Side pots
        )

        # Create dictionary of all bets from players who contributed
        posted_amounts = {
            p: p.bet
            for p in active_players
            if p.bet > 0  # Include all bets, even from folded players
        }
        if not posted_amounts:
            # If no new bets, return existing side pots
            return self.side_pots if self.side_pots else []

        # Calculate new side pots from current bets
        new_side_pots = []
        current_amount = 0

        # Sort players by their bet amounts
        sorted_players = sorted(posted_amounts.items(), key=lambda x: x[1])

        # Track processed amounts to avoid double counting
        processed_amounts = {}

        for player, amount in sorted_players:
            if amount > current_amount:
                # Players are eligible if they:
                # 1. Bet at least this amount
                # 2. Haven't folded
                eligible = [
                    p
                    for p, bet in posted_amounts.items()
                    if bet >= amount and not p.folded
                ]

                # Calculate pot size for this level
                contribution = amount - current_amount
                contributors = sum(
                    1 for bet in posted_amounts.values() if bet >= amount
                )
                pot_size = contribution * contributors

                # Only create a new side pot if it would have a positive amount
                # and hasn't been processed at this level
                if pot_size > 0 and amount not in processed_amounts:
                    # Always create new pots for current betting round
                    new_side_pots.append(
                        SidePot(
                            amount=pot_size, eligible_players=[p.name for p in eligible]
                        )
                    )
                    PotLogger.log_new_side_pot(pot_size, [p.name for p in eligible])
                    processed_amounts[amount] = pot_size

                current_amount = amount

        # Combine existing and new pots
        final_pots = []
        if self.side_pots:
            final_pots.extend(self.side_pots)  # Keep existing pots first
        final_pots.extend(new_side_pots)  # Add new pots from this round

        # Merge pots with identical eligible players
        merged_pots = {}
        for side_pot in final_pots:
            # Use frozenset of eligible players as key for merging
            key = frozenset(side_pot.eligible_players)
            if key not in merged_pots:
                merged_pots[key] = side_pot.amount
            else:
                merged_pots[key] += side_pot.amount
                PotLogger.log_pot_merge(side_pot.amount, list(key))

        # Convert merged pots back to list format
        final_pots = [
            SidePot(amount=amount, eligible_players=sorted(list(players)))
            for players, amount in merged_pots.items()
        ]

        # Validate total chips haven't changed
        total_chips_after = (
            sum(p.chips for p in active_players)  # Current chips
            + self.pot  # Main pot
            + sum(pot.amount for pot in final_pots)  # All side pots
        )

        if total_chips_before != total_chips_after:
            raise InvalidGameStateError(
                f"Chip total mismatch in side pot calculation: {total_chips_before} vs {total_chips_after}"
            )

        self.side_pots = final_pots
        return final_pots

    def get_side_pots_view(self) -> List[Dict[str, Any]]:
        """
        Get a display-friendly view of the current side pots.

        Returns:
            List[Dict[str, Any]]: List of dictionaries containing:
                - amount: The amount in the side pot
                - eligible_players: List of player names eligible for this pot
        """
        if not self.side_pots:
            return []
        return [
            {"amount": pot.amount, "eligible_players": pot.eligible_players}
            for pot in self.side_pots
        ]

    def log_side_pots(self, logger) -> None:
        """
        Log the current side pot state.
        """
        if not self.side_pots:
            return
        PotLogger.log_side_pots_info(self.side_pots)

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

        PotLogger.log_pot_update(old_pot, main_pot, old_side_pots, side_pots)

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
            PotLogger.log_pot_validation_error(
                total_bets,
                total_in_pots,
                self.pot,
                self.side_pots,
                [(p.name, p.chips, p.bet) for p in active_players],
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
                PotLogger.log_chip_mismatch(
                    initial_total,
                    current_total,
                    [(p.name, p.chips) for p in active_players],
                    {"main": self.pot, "side": self.side_pots},
                    [(p.name, p.bet) for p in active_players],
                )
                raise InvalidGameStateError(
                    f"Total chips changed: initial={initial_total}, current={current_total}"
                )

        return True

    def end_betting_round(self, active_players: List[Player]) -> None:
        """
        Handle the end of a betting round.

        This method should be called AFTER calculate_side_pots (if needed). It moves
        all current bets into the main pot and resets player bet amounts to 0.

        Args:
            active_players: List of players still in the hand

        Side Effects:
            - Adds current bets to main pot
            - Clears player bet amounts to 0
            - Logs betting round completion

        Note:
            - Call calculate_side_pots first if side pots are needed
            - This method moves ALL current bets to the main pot
            - Player bet amounts are reset to 0 after moving to pot
        """
        # Add current bets to pot
        total_bets = sum(p.bet for p in active_players)
        self.add_to_pot(total_bets)

        # Clear player bets
        for player in active_players:
            player.bet = 0

        # Log for debugging
        PotLogger.log_betting_round_end(self.pot)

    def get_state(self) -> PotState:
        """Get the current state of all pots."""
        return PotState(
            main_pot=self.pot,
            side_pots=(
                self.side_pots if self.side_pots else []
            ),  # Convert None to empty list
            total_pot=self.pot
            + sum(pot.amount for pot in (self.side_pots or [])),  # Handle None case
        )
