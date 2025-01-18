from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from data.types.pot_types import PotState, SidePot
from exceptions import InvalidGameStateError
from tests.mocks.mock_player import MockPlayer


class MockPotManager:
    """A mock implementation of the PotManager class for testing purposes.

    This mock provides the same interface as the real PotManager but with configurable
    behaviors for testing. It tracks pot amounts and side pots while allowing easy
    configuration of test scenarios.

    Usage:
        # Basic initialization
        pot_manager = MockPotManager()

        # Configure specific test scenarios
        pot_manager.configure_for_test(
            pot=100,  # Set main pot amount
            side_pots=[SidePot(amount=50, eligible_players=["P1", "P2"])],
            validation_result=True  # Configure pot validation behavior
        )

        # Configure side pots directly
        pot_manager.set_side_pots([
            SidePot(amount=100, eligible_players=["P1", "P2"]),
            SidePot(amount=50, eligible_players=["P1"])
        ])

        # Test error scenarios
        pot_manager.configure_for_test(
            raise_validation_error=True  # Make validate_pot_state raise an error
        )

        # Access mock methods for verification
        pot_manager.add_to_pot.assert_called_with(50)
        pot_manager.calculate_side_pots.assert_called_once()

    Default Behaviors:
        - add_to_pot: Adds amount to main pot, raises ValueError for negative amounts
        - calculate_side_pots: Creates side pots for all-in players
        - validate_pot_state: Performs basic validation of pot consistency
        - end_betting_round: Collects bets into pot and resets player bets
        - reset_pot: Clears main pot and side pots

    All methods are MagicMocks that can be configured with custom return values
    or side effects as needed for testing.
    """

    def __init__(self):
        """Initialize a mock pot manager with empty pot and no side pots."""
        self.pot: int = 0
        self.side_pots: Optional[List[SidePot]] = None

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

        # Basic side pot calculation for all-in players
        all_in_players = [p for p in active_players if p.is_all_in]
        if all_in_players:
            # Create a simple side pot for each all-in player
            new_side_pots = []
            for player in all_in_players:
                eligible = [
                    p.name
                    for p in active_players
                    if not p.folded and p.bet >= player.bet
                ]
                new_side_pots.append(
                    SidePot(
                        amount=player.bet * len(eligible), eligible_players=eligible
                    )
                )
            self.side_pots = new_side_pots
            return new_side_pots

        return self.side_pots if self.side_pots else []

    def _default_reset_pot(self) -> None:
        """Default behavior for resetting the pot."""
        self.pot = 0
        self.side_pots = None

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
        """Default behavior for ending betting round."""
        total_bets = sum(p.bet for p in active_players)
        self.add_to_pot(total_bets)
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
        return f"MockPotManager: {self.pot} in main pot{side_pots_str}"
