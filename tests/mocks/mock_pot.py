from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from data.types.pot_types import PotState, SidePot
from exceptions import InvalidGameStateError
from tests.mocks.mock_player import MockPlayer


class MockPot:
    """A mock implementation of the Pot class for testing purposes.

    This mock provides the same interface as the real Pot but with configurable
    behaviors for testing. It tracks pot amounts and side pots while allowing easy
    configuration of test scenarios. It includes logging functionality and maintains
    total chip consistency across all operations.

    Usage:
        # Basic initialization
        pot = MockPot()

        # Configure specific test scenarios
        pot.configure_for_test(
            pot=100,  # Set main pot amount
            side_pots=[SidePot(amount=50, eligible_players=["P1", "P2"])],
            validation_result=True  # Configure pot validation behavior
        )

        # Configure side pots directly
        pot.set_side_pots([
            SidePot(amount=100, eligible_players=["P1", "P2"]),
            SidePot(amount=50, eligible_players=["P1"])
        ])

        # Test error scenarios
        pot.configure_for_test(
            raise_validation_error=True  # Make validate_pot_state raise an error
        )

        # Access mock methods for verification
        pot.add_to_pot.assert_called_with(50)
        pot.calculate_side_pots.assert_called_once()

        # Verify logging calls
        pot.log_pot_change.assert_called_with(old_amount, new_amount, change)
        pot.log_new_side_pot.assert_called_with(amount, eligible_players)

    Default Behaviors:
        - add_to_pot: Adds amount to main pot, raises ValueError for negative amounts
        - calculate_side_pots: Creates side pots based on player bets and all-ins,
          merging with existing pots and maintaining chip consistency
        - validate_pot_state: Validates pot consistency and total chips in play
        - end_betting_round: Collects bets into pot and resets player bets
        - reset_pot: Clears main pot and side pots
        - get_state: Returns current PotState with main pot, side pots, and total
        - get_side_pots_view: Returns formatted view of current side pots

    Logging Methods:
        - log_pot_change: Logs changes to pot amounts
        - log_pot_reset: Logs pot resets
        - log_new_side_pot: Logs creation of new side pots
        - log_pot_validation_error: Logs validation errors
        - log_chip_mismatch: Logs chip total mismatches
        - log_betting_round_end: Logs end of betting rounds
        - log_pot_update: Logs updates to pot state

    All methods are MagicMocks that can be configured with custom return values
    or side effects as needed for testing. The default implementations match
    the behavior of the real Pot class while allowing easy configuration for
    specific test scenarios.
    """

    def __init__(self) -> None:
        """Initialize a mock pot with empty pot and no side pots."""
        self.pot: int = 0
        self.side_pots: List[SidePot] = []

        # Create mock methods that can be configured in tests
        self.add_to_pot = MagicMock()
        self.calculate_side_pots = MagicMock(return_value=[])
        self.reset_pot = MagicMock()
        self.validate_pot_state = MagicMock(return_value=True)
        self.end_betting_round = MagicMock()
        self.log_side_pots = MagicMock()

        # Set up default behaviors
        self.add_to_pot.side_effect = self._default_add_to_pot
        self.calculate_side_pots.side_effect = self._default_calculate_side_pots
        self.reset_pot.side_effect = self._default_reset_pot
        self.validate_pot_state.side_effect = self._default_validate_pot_state
        self.end_betting_round.side_effect = self._default_end_betting_round

        # Add mock loggers
        self.log_pot_change = MagicMock()
        self.log_pot_reset = MagicMock()
        self.log_new_side_pot = MagicMock()
        self.log_pot_validation_error = MagicMock()
        self.log_chip_mismatch = MagicMock()
        self.log_betting_round_end = MagicMock()
        self.log_pot_update = MagicMock()

    def _default_add_to_pot(self, amount: int) -> None:
        """Default behavior for adding to pot."""
        if amount < 0:
            raise ValueError("Cannot add negative amount to pot")
        self.pot += amount

    def _default_calculate_side_pots(
        self, active_players: List[MockPlayer]
    ) -> List[SidePot]:
        """Default behavior for calculating side pots."""
        if not active_players:
            self.side_pots = []
            return []

        # Track total chips before calculation
        total_chips_before = (
            sum(p.chips + p.bet for p in active_players)  # Current chips + bets
            + self.pot  # Main pot
            + (
                sum(pot.amount for pot in self.side_pots) if self.side_pots else 0
            )  # Side pots
        )

        # Add validation before processing
        total_bets = sum(p.bet for p in active_players)
        if total_bets == 0:
            return self.side_pots if self.side_pots else []

        # Create dictionary of all bets from players who contributed
        posted_amounts = {
            p: p.bet
            for p in active_players
            if p.bet > 0  # Include all bets, even from folded players
        }
        if not posted_amounts:
            return self.side_pots if self.side_pots else []

        # Keep track of existing side pots
        existing_pots = self.side_pots if self.side_pots else []

        # Calculate new side pots from current bets
        new_side_pots = []
        current_amount = 0
        processed_amounts = {}

        # Sort players by their bet amounts
        sorted_players = sorted(posted_amounts.items(), key=lambda x: x[1])

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

                if pot_size > 0 and amount not in processed_amounts:
                    new_side_pots.append(
                        SidePot(
                            amount=pot_size, eligible_players=[p.name for p in eligible]
                        )
                    )
                    processed_amounts[amount] = pot_size

                current_amount = amount

        # Merge pots with identical eligible players
        merged_pots = {}
        # First add existing pots to merged_pots
        if existing_pots:
            for existing_pot in existing_pots:
                key = frozenset(existing_pot.eligible_players)
                if key not in merged_pots:
                    merged_pots[key] = existing_pot.amount
                else:
                    merged_pots[key] += existing_pot.amount

        # Then merge new pots, combining with existing ones if they have same eligible players
        for side_pot in new_side_pots:
            # Use frozenset of eligible players as key for merging
            key = frozenset(side_pot.eligible_players)
            if key not in merged_pots:
                merged_pots[key] = side_pot.amount
            else:
                merged_pots[key] += side_pot.amount

        # Convert merged pots to final format
        final_pots = [
            SidePot(amount=amount, eligible_players=sorted(list(players)))
            for players, amount in merged_pots.items()
        ]

        # Verify all current bets were processed
        total_in_new_pots = sum(pot.amount for pot in final_pots)
        if total_in_new_pots != total_bets + sum(p.amount for p in existing_pots):
            raise InvalidGameStateError(
                f"Not all bets processed: bets={total_bets}, pots={total_in_new_pots}"
            )

        self.side_pots = final_pots
        return final_pots

    def _default_reset_pot(self) -> None:
        """Default behavior for resetting the pot."""
        self.pot = 0
        self.side_pots = []

    def _default_validate_pot_state(
        self, active_players: List[MockPlayer], initial_total: Optional[int] = None
    ) -> bool:
        """Default behavior for validating pot state."""
        # Calculate total chips in play
        total_chips = sum(p.chips for p in active_players)
        total_in_pots = self.pot + (
            sum(pot.amount for pot in self.side_pots) if self.side_pots else 0
        )
        total_bets = sum(p.bet for p in active_players)

        # Basic validation checks
        if total_bets > total_in_pots:
            raise InvalidGameStateError(
                f"Current bets exceed pot: bets={total_bets}, pots={total_in_pots}"
            )

        if initial_total is not None:
            current_total = total_chips + total_in_pots
            if current_total != initial_total:
                raise InvalidGameStateError(
                    f"Total chips changed: initial={initial_total}, current={current_total}"
                )

        return True

    def _default_end_betting_round(self, active_players: List[MockPlayer]) -> None:
        """Default behavior for ending betting round.

        This should be called AFTER calculate_side_pots if side pots are needed.
        """
        # Add current bets to pot
        total_bets = sum(p.bet for p in active_players)
        self.add_to_pot(total_bets)

        # Clear player bets
        for player in active_players:
            player.bet = 0

    def configure_for_test(
        self,
        pot: Optional[int] = None,
        side_pots: Optional[List[SidePot]] = None,
        validation_result: Optional[bool] = None,
        raise_validation_error: bool = False,
    ) -> None:
        """Configure the mock pot manager for testing.

        Args:
            pot: Optional amount to set as main pot
            side_pots: Optional list of side pots to set
            validation_result: Optional boolean for validate_pot_state to return
            raise_validation_error: Whether validate_pot_state should raise an error
        """
        if pot is not None:
            self.pot = pot

        if side_pots is not None:
            self.side_pots = side_pots

        if validation_result is not None:
            if raise_validation_error:
                self.validate_pot_state.side_effect = InvalidGameStateError(
                    "Test error"
                )
            else:
                self.validate_pot_state.return_value = validation_result

    def set_side_pots(self, side_pots: List[SidePot]) -> None:
        """Configure the side pots for testing."""
        self.side_pots = side_pots
        self.calculate_side_pots.return_value = side_pots

    def get_side_pots_view(self) -> List[Dict[str, Any]]:
        """Get a display-friendly view of the current side pots."""
        if not self.side_pots:
            return []
        return [
            {"amount": pot.amount, "eligible_players": pot.eligible_players}
            for pot in self.side_pots
        ]

    def set_pots(
        self, main_pot: int, side_pots: Optional[List[SidePot]] = None
    ) -> None:
        """Set the main pot and side pots directly."""
        if main_pot < 0:
            raise ValueError("Main pot cannot be negative")
        self.pot = main_pot
        self.side_pots = side_pots

    def get_state(self) -> PotState:
        """Get the current state of all pots."""
        return PotState(
            main_pot=self.pot,
            side_pots=self.side_pots if self.side_pots else [],
            total_pot=self.pot + sum(pot.amount for pot in (self.side_pots or [])),
        )

    def __str__(self) -> str:
        """Get a string representation of the pot state."""
        side_pots_str = f", {len(self.side_pots)} side pots" if self.side_pots else ""
        return f"MockPot: {self.pot} in main pot{side_pots_str}"

    def log_side_pots(self) -> None:
        """Mock implementation of log_side_pots."""
        if not self.side_pots:
            return
        self.log_side_pots_info(self.side_pots)
