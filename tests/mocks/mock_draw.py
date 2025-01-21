from typing import TYPE_CHECKING, List, Optional
from unittest.mock import MagicMock

if TYPE_CHECKING:
    from game.card import Card

from loggers.draw_logger import DrawLogger
from tests.mocks.mock_deck import MockDeck
from tests.mocks.mock_player import MockPlayer


class MockDraw:
    """A mock implementation of draw phase functionality for testing purposes.

    This mock provides configurable behaviors for testing the draw phase where players
    can discard and draw new cards. It tracks discard decisions and allows easy
    configuration of draw outcomes.

    Usage:
        # Basic initialization
        draw = MockDraw()

        # Configure specific discard decisions
        draw.set_discard_decision(
            player_name="TestPlayer",
            discard_indices=[0, 1],  # Cards to discard
            should_raise_error=False
        )

        # Configure draw outcomes
        draw.set_draw_outcome(
            player_name="TestPlayer",
            new_cards=[Card("A", "♠"), Card("K", "♠")]
        )

        # Test draw phase
        draw.handle_draw_phase(game_mock)

        # Verify method calls
        draw.handle_draw_phase.assert_called_once()
        draw.get_discard_indices.assert_called_with(player_mock)

    Default Behaviors:
        - handle_draw_phase: Processes each player's draw decisions
        - get_discard_indices: Returns configured discard indices or None
        - process_discard_and_draw: Handles discarding and drawing new cards
        - handle_preemptive_reshuffle: Manages deck reshuffling if needed
    """

    def __init__(self):
        """Initialize mock draw handler with default configurations."""
        # Create mock methods
        self.handle_draw_phase = MagicMock()
        self.get_discard_indices = MagicMock()
        self.process_discard_and_draw = MagicMock()
        self.handle_preemptive_reshuffle = MagicMock()

        # Set up default behaviors
        self.handle_draw_phase.side_effect = self._default_handle_draw_phase
        self.get_discard_indices.side_effect = self._default_get_discard_indices
        self.process_discard_and_draw.side_effect = (
            self._default_process_discard_and_draw
        )
        self.handle_preemptive_reshuffle.side_effect = (
            self._default_handle_preemptive_reshuffle
        )

        # Configuration state
        self._discard_decisions = {}  # player_name -> (indices, should_raise)
        self._draw_outcomes = {}  # player_name -> new_cards
        self._should_raise_error = False
        self._error_message = "Mock Draw Error"

    def _default_handle_draw_phase(self, game) -> None:
        """Default behavior for handling draw phase."""
        if self._should_raise_error:
            raise ValueError(self._error_message)

        active_players = [
            p for p in game.players if not p.folded and hasattr(p, "decide_discard")
        ]
        max_possible_draws = len(active_players) * 5  # MAX_DISCARD = 5

        self.handle_preemptive_reshuffle(game.deck, max_possible_draws)

        for player in game.players:
            if player.folded:
                continue

            discard_indices = self.get_discard_indices(player)
            if discard_indices is None:
                DrawLogger.log_keep_hand(
                    player.name,
                    explicit_decision=(
                        False if not hasattr(player, "decide_discard") else True
                    ),
                )
                continue

            if discard_indices:
                self.process_discard_and_draw(player, game.deck, discard_indices)
            else:
                DrawLogger.log_keep_hand(player.name, explicit_decision=True)

    def _default_get_discard_indices(self, player: MockPlayer) -> Optional[List[int]]:
        """Default behavior for getting discard indices."""
        if not hasattr(player, "decide_discard"):
            DrawLogger.log_non_ai_player()
            return None

        decision = self._discard_decisions.get(player.name)
        if decision is None:
            return []

        indices, should_raise = decision
        if should_raise:
            DrawLogger.log_draw_error(player.name, ValueError("Test error"))
            return None

        if len(indices) > 5:  # MAX_DISCARD = 5
            DrawLogger.log_discard_validation_error(player.name, len(indices))
            indices = indices[:5]

        if any(idx < 0 or idx >= 5 for idx in indices):
            DrawLogger.log_invalid_indexes(player.name)
            return None

        return indices

    def _default_process_discard_and_draw(
        self, player: MockPlayer, deck: MockDeck, discard_indices: List[int]
    ) -> None:
        """Default behavior for processing discards and draws."""
        discard_count = len(discard_indices)
        DrawLogger.log_discard_action(player.name, discard_count)

        # Handle discarding
        discarded_cards = [player.hand.cards[idx] for idx in discard_indices]
        deck.add_discarded(discarded_cards)
        player.hand.remove_cards(discard_indices)

        # Handle drawing
        if deck.needs_reshuffle(discard_count):
            if len(deck.cards) == discard_count:
                DrawLogger.log_reshuffle_status(discard_count, 0, skip=True)
            else:
                DrawLogger.log_reshuffle_status(discard_count, deck.remaining_cards())
                deck.reshuffle_all()

        # Use configured draw outcome or default to deck's deal
        new_cards = self._draw_outcomes.get(player.name) or deck.deal(discard_count)
        player.hand.add_cards(new_cards)

        DrawLogger.log_deck_status(player.name, deck.remaining_cards())

    def _default_handle_preemptive_reshuffle(
        self, deck: MockDeck, needed_cards: int
    ) -> None:
        """Default behavior for handling preemptive reshuffle."""
        if deck.needs_reshuffle(needed_cards):
            if len(deck.cards) == needed_cards:
                DrawLogger.log_preemptive_reshuffle(needed_cards, skip=True)
            else:
                DrawLogger.log_preemptive_reshuffle(
                    needed_cards, deck.remaining_cards()
                )
                deck.reshuffle_all()

    def set_discard_decision(
        self,
        player_name: str,
        discard_indices: List[int],
        should_raise_error: bool = False,
    ) -> None:
        """Configure discard decision for a player.

        Args:
            player_name: Name of the player
            discard_indices: List of card indices to discard
            should_raise_error: Whether to simulate an error
        """
        self._discard_decisions[player_name] = (discard_indices, should_raise_error)
        self.get_discard_indices.reset_mock()

    def set_draw_outcome(self, player_name: str, new_cards: List["Card"]) -> None:
        """Configure the cards a player will draw.

        Args:
            player_name: Name of the player
            new_cards: List of cards to draw
        """
        self._draw_outcomes[player_name] = new_cards
        self.process_discard_and_draw.reset_mock()

    def configure_for_test(
        self,
        should_raise_error: bool = False,
        error_message: Optional[str] = None,
    ) -> None:
        """Configure the mock draw handler's behavior for testing.

        Args:
            should_raise_error: Whether methods should raise errors
            error_message: Custom error message when raising errors
        """
        self._should_raise_error = should_raise_error
        if error_message:
            self._error_message = error_message

    def reset(self) -> None:
        """Reset the mock draw handler to default state."""
        self._discard_decisions.clear()
        self._draw_outcomes.clear()
        self._should_raise_error = False
        self._error_message = "Mock Draw Error"

        self.handle_draw_phase.reset_mock()
        self.get_discard_indices.reset_mock()
        self.process_discard_and_draw.reset_mock()
        self.handle_preemptive_reshuffle.reset_mock()

    def __str__(self) -> str:
        """Get string representation of mock draw handler state."""
        return (
            f"MockDraw: {len(self._discard_decisions)} discard decisions, "
            f"{len(self._draw_outcomes)} draw outcomes configured"
        )
