from typing import List, Optional, Tuple, Union
from unittest.mock import MagicMock

from data.types.pot_types import SidePot
from tests.mocks.mock_player import MockPlayer


class MockBetting:
    """A mock implementation of betting functionality for testing purposes.

    This mock provides configurable behaviors for testing betting rounds and actions.
    It tracks betting state and allows easy configuration of betting outcomes.

    Usage:
        # Basic initialization
        betting = MockBetting()

        # Configure specific betting round outcome
        betting.set_betting_round_result(
            pot_amount=100,
            side_pots=[SidePot(amount=50, eligible_players=["P1", "P2"])],
            should_continue=True
        )

        # Configure blind collection
        betting.set_blind_collection_result(
            total_collected=30,  # Total amount collected from blinds/antes
            sb_amount=10,        # Amount collected from small blind
            bb_amount=20         # Amount collected from big blind
        )

        # Test betting round
        result = betting.handle_betting_round(game_mock)
        assert result[0] == 100  # Check pot amount
        assert len(result[1]) == 1  # Check side pots
        assert result[2] == True  # Check should_continue

        # Verify method calls
        betting.handle_betting_round.assert_called_once()
        betting.collect_blinds_and_antes.assert_called_with(
            players_mock, dealer_idx, sb, bb, ante, game_mock
        )

    Default Behaviors:
        - handle_betting_round: Returns configured result or default values
        - collect_blinds_and_antes: Returns configured amount or default 0
        - betting_round: Returns configured pot amount or default 0
        - validate_bet_to_call: Returns configured amount or calculates difference
    """

    def __init__(self):
        """Initialize mock betting with default configurations."""
        # Create mock methods
        self.handle_betting_round = MagicMock()
        self.collect_blinds_and_antes = MagicMock()
        self.betting_round = MagicMock()
        self.validate_bet_to_call = MagicMock()

        # Set up default behaviors
        self.handle_betting_round.side_effect = self._default_handle_betting_round
        self.collect_blinds_and_antes.side_effect = self._default_collect_blinds_and_antes
        self.betting_round.side_effect = self._default_betting_round
        self.validate_bet_to_call.side_effect = self._default_validate_bet_to_call

        # Configuration state
        self._betting_round_result = None
        self._blind_collection_result = None
        self._bet_to_call_amount = None
        self._should_raise_error = False
        self._error_message = "Mock Betting Error"

    def _default_handle_betting_round(self, game) -> Tuple[int, Optional[List[SidePot]], bool]:
        """Default behavior for handling betting round."""
        if self._should_raise_error:
            raise ValueError(self._error_message)

        if self._betting_round_result:
            return self._betting_round_result

        # Default return values
        return 0, None, True

    def _default_collect_blinds_and_antes(
        self, players, dealer_index, small_blind, big_blind, ante, game
    ) -> int:
        """Default behavior for collecting blinds and antes."""
        if self._blind_collection_result:
            return self._blind_collection_result["total_collected"]

        # Default to collecting small blind + big blind
        return small_blind + big_blind

    def _default_betting_round(self, game) -> Union[int, Tuple[int, List[SidePot]]]:
        """Default behavior for betting round."""
        if self._betting_round_result:
            pot, side_pots, _ = self._betting_round_result
            if side_pots:
                return pot, side_pots
            return pot
        return 0

    def _default_validate_bet_to_call(self, current_bet: int, player_bet: int) -> int:
        """Default behavior for validating bet to call."""
        if self._bet_to_call_amount is not None:
            return self._bet_to_call_amount
        return max(0, current_bet - player_bet)

    def set_betting_round_result(
        self,
        pot_amount: int = 0,
        side_pots: Optional[List[SidePot]] = None,
        should_continue: bool = True,
    ) -> None:
        """Configure the result of a betting round.

        Args:
            pot_amount: Final pot amount
            side_pots: Optional list of side pots
            should_continue: Whether game should continue
        """
        self._betting_round_result = (pot_amount, side_pots, should_continue)
        self.handle_betting_round.reset_mock()
        self.betting_round.reset_mock()

    def set_blind_collection_result(
        self,
        total_collected: int,
        sb_amount: Optional[int] = None,
        bb_amount: Optional[int] = None,
    ) -> None:
        """Configure the result of blind collection.

        Args:
            total_collected: Total amount collected
            sb_amount: Amount collected from small blind
            bb_amount: Amount collected from big blind
        """
        self._blind_collection_result = {
            "total_collected": total_collected,
            "sb_amount": sb_amount,
            "bb_amount": bb_amount,
        }
        self.collect_blinds_and_antes.reset_mock()

    def set_bet_to_call(self, amount: int) -> None:
        """Configure the amount needed to call.

        Args:
            amount: Amount needed to call
        """
        self._bet_to_call_amount = amount
        self.validate_bet_to_call.reset_mock()

    def configure_for_test(
        self,
        betting_result: Optional[Tuple[int, Optional[List[SidePot]], bool]] = None,
        blind_collection: Optional[dict] = None,
        bet_to_call: Optional[int] = None,
        should_raise_error: bool = False,
        error_message: Optional[str] = None,
    ) -> None:
        """Configure the mock betting behavior for testing.

        Args:
            betting_result: Optional tuple of (pot, side_pots, should_continue)
            blind_collection: Optional dict with blind collection results
            bet_to_call: Optional amount needed to call
            should_raise_error: Whether methods should raise errors
            error_message: Custom error message when raising errors
        """
        if betting_result is not None:
            self._betting_round_result = betting_result

        if blind_collection is not None:
            self._blind_collection_result = blind_collection

        if bet_to_call is not None:
            self._bet_to_call_amount = bet_to_call

        self._should_raise_error = should_raise_error
        if error_message:
            self._error_message = error_message

    def reset(self) -> None:
        """Reset the mock betting to default state."""
        self._betting_round_result = None
        self._blind_collection_result = None
        self._bet_to_call_amount = None
        self._should_raise_error = False
        self._error_message = "Mock Betting Error"

        self.handle_betting_round.reset_mock()
        self.collect_blinds_and_antes.reset_mock()
        self.betting_round.reset_mock()
        self.validate_bet_to_call.reset_mock()

    def __str__(self) -> str:
        """Get string representation of mock betting state."""
        result_str = (
            f"{self._betting_round_result[0]} in pot"
            if self._betting_round_result
            else "No betting result"
        )
        return f"MockBetting: {result_str}" 