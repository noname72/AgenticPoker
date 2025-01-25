from typing import Optional
from unittest.mock import MagicMock


class MockBetting:
    """A mock implementation of betting functionality for testing purposes.

    This mock provides configurable behaviors for testing betting rounds and actions
    from game/betting.py. It mocks the three main functions:
    - handle_betting_round: Returns whether betting should continue
    - betting_round: Processes a complete round of betting
    - collect_blinds_and_antes: Handles forced bets at start of hand

    Usage:
        # Basic initialization
        betting = MockBetting()

        # Configure betting round result
        betting.set_betting_round_result(should_continue=True)

        # Configure blind collection
        betting.set_blind_collection_result(total_collected=30)

        # Test betting round
        result = betting.handle_betting_round(game_mock)
        assert result == True  # Check if betting should continue

        # Verify method calls
        betting.handle_betting_round.assert_called_once()
        betting.collect_blinds_and_antes.assert_called_with(
            game_mock, dealer_idx, sb, bb, ante
        )

    Default Behaviors:
        - handle_betting_round: Returns True (continue) unless configured otherwise
        - collect_blinds_and_antes: Returns sum of small_blind + big_blind unless configured
        - betting_round: No-op function that processes betting actions
    """

    def __init__(self):
        """Initialize mock betting with default configurations."""
        # Create mock methods
        self.handle_betting_round = MagicMock()
        self.collect_blinds_and_antes = MagicMock()
        self.betting_round = MagicMock()

        # Set up default behaviors
        self.handle_betting_round.side_effect = self._default_handle_betting_round
        self.collect_blinds_and_antes.side_effect = (
            self._default_collect_blinds_and_antes
        )
        self.betting_round.side_effect = self._default_betting_round

        # Configuration state
        self._should_continue = True
        self._blind_collection_result = None
        self._should_raise_error = False
        self._error_message = "Mock Betting Error"

    def _default_handle_betting_round(self, game) -> bool:
        """Default behavior for handling betting round.

        Args:
            game: Game object containing game state

        Returns:
            bool: Whether betting should continue (True if multiple players remain)

        Raises:
            ValueError: If configured to raise error
        """
        if self._should_raise_error:
            raise ValueError(self._error_message)
        return self._should_continue

    def _default_collect_blinds_and_antes(
        self, game, dealer_index, small_blind, big_blind, ante
    ) -> int:
        """Default behavior for collecting blinds and antes.

        Args:
            game: Game object containing game state
            dealer_index: Position of dealer button
            small_blind: Amount of small blind
            big_blind: Amount of big blind
            ante: Amount of ante (0 if no ante)

        Returns:
            int: Total amount collected from blinds and antes
        """
        if self._blind_collection_result:
            return self._blind_collection_result["total_collected"]
        return small_blind + big_blind

    def _default_betting_round(self, game) -> None:
        """Default behavior for processing a complete betting round.

        Args:
            game: Game object containing game state
        """
        pass

    def set_betting_round_result(self, should_continue: bool = True) -> None:
        """Configure the result of handle_betting_round.

        Args:
            should_continue: Whether betting should continue (True if multiple players remain)
        """
        self._should_continue = should_continue
        self.handle_betting_round.reset_mock()
        self.betting_round.reset_mock()

    def set_blind_collection_result(
        self,
        total_collected: int,
        sb_amount: Optional[int] = None,
        bb_amount: Optional[int] = None,
    ) -> None:
        """Configure the result of blind and ante collection.

        Args:
            total_collected: Total amount collected from all forced bets
            sb_amount: Optional amount collected from small blind (for verification)
            bb_amount: Optional amount collected from big blind (for verification)
        """
        self._blind_collection_result = {
            "total_collected": total_collected,
            "sb_amount": sb_amount,
            "bb_amount": bb_amount,
        }
        self.collect_blinds_and_antes.reset_mock()

    def configure_for_test(
        self,
        betting_result: Optional[bool] = None,
        blind_collection: Optional[dict] = None,
        should_raise_error: bool = False,
        error_message: Optional[str] = None,
    ) -> None:
        """Configure all mock betting behaviors for a test.

        Args:
            betting_result: Optional boolean for whether betting should continue
            blind_collection: Optional dict with blind collection results
            should_raise_error: Whether methods should raise errors
            error_message: Custom error message when raising errors
        """
        if betting_result is not None:
            self._should_continue = betting_result

        if blind_collection is not None:
            self._blind_collection_result = blind_collection

        self._should_raise_error = should_raise_error
        if error_message:
            self._error_message = error_message

    def reset(self) -> None:
        """Reset the mock betting to default state.

        Resets:
        - should_continue to True
        - blind collection results to None
        - error state to False
        - All mock call histories
        """
        self._should_continue = True
        self._blind_collection_result = None
        self._should_raise_error = False
        self._error_message = "Mock Betting Error"

        self.handle_betting_round.reset_mock()
        self.collect_blinds_and_antes.reset_mock()
        self.betting_round.reset_mock()

    def __str__(self) -> str:
        """Get string representation of mock betting state.

        Returns:
            str: Description of current mock betting configuration
        """
        return f"MockBetting: should_continue={self._should_continue}"
