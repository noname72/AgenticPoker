from typing import List, Optional, Tuple
from unittest.mock import MagicMock

from data.types.hand_types import HandState
from game.card import Card


class MockHand:
    """A mock implementation of the Hand class for testing purposes.

    This mock provides the same interface as the real Hand class but with configurable
    behaviors for testing. It allows easy configuration of hand rankings and comparison
    behaviors without needing actual card evaluation.

    Usage:
        # Basic initialization
        hand = MockHand()

        # Initialize with specific cards
        hand = MockHand([Card("A", "♠"), Card("K", "♠")])

        # Configure hand ranking
        hand.set_rank(
            rank=1,  # Royal Flush (lower is better)
            tiebreakers=[14, 13, 12, 11, 10],  # Card values for comparison
            description="Royal Flush"  # Text description of hand
        )

        # Configure for test with single method
        hand.configure_for_test(
            cards=[Card("A", "♠"), Card("K", "♠")],
            rank=1,
            tiebreakers=[14, 13],
            description="Ace-King High"
        )

        # Test hand comparison
        other_hand = MockHand()
        other_hand.set_rank(2, [13, 12], "Straight Flush")
        assert hand > other_hand  # Royal Flush beats Straight Flush

        # Verify method calls
        hand.add_cards.assert_called_once()
        hand.evaluate.assert_called_with()

    Default Behaviors:
        - add_cards: Adds cards to hand and invalidates rank
        - remove_cards: Removes cards by position and invalidates rank
        - evaluate: Returns configured rank or raises error if not configured
        - get_state: Returns current HandState
        - Comparison operators use poker hand ranking rules (lower rank is better)

    Attributes:
        cards (List[Card]): Current cards in hand
        _rank (Optional[Tuple[int, List[int], str]]): Configured rank info:
            - int: Hand rank (lower is better)
            - List[int]: Tiebreaker values (higher is better)
            - str: Hand description

    All methods are MagicMocks that can be configured with custom return values
    or side effects as needed for testing.

    Note:
        - Hand comparison follows poker rules where lower rank numbers are better
        - Tiebreaker values follow opposite rule where higher numbers are better
        - Invalid hands (not configured or wrong number of cards) return infinite rank
    """

    def __init__(self, cards: Optional[List[Card]] = None):
        """Initialize a mock hand with optional starting cards."""
        self.cards = cards if cards is not None else []
        self._rank: Optional[Tuple[int, List[int], str]] = None

        # Create mock methods that can be configured in tests
        self.add_cards = MagicMock()
        self.remove_cards = MagicMock()
        self.evaluate = MagicMock()

        # Set up default behaviors
        self.add_cards.side_effect = self._default_add_cards
        self.remove_cards.side_effect = self._default_remove_cards
        self.evaluate.side_effect = self._default_evaluate

    def _default_add_cards(self, cards: List[Card]) -> None:
        """Default behavior for adding cards."""
        if cards is None:
            raise TypeError("Cannot add None as cards")
        if not isinstance(cards, list):
            raise TypeError("Cards must be provided as a list")
        if any(not isinstance(card, Card) for card in cards):
            raise TypeError("All elements must be Card objects")
        self.cards.extend(cards)
        self._rank = None

    def _default_remove_cards(self, positions: List[int]) -> None:
        """Default behavior for removing cards."""
        for idx in sorted(positions, reverse=True):
            self.cards.pop(idx)
        self._rank = None

    def _default_evaluate(self) -> Tuple[int, List[int], str]:
        """Default evaluation behavior."""
        if not self.cards or len(self.cards) != 5:
            raise ValueError("Cannot evaluate hand: incorrect number of cards")

        if self._rank is None:
            raise ValueError("Hand rank not configured for testing")

        return self._rank

    def set_rank(self, rank: int, tiebreakers: List[int], description: str) -> None:
        """Configure the hand's rank for testing purposes.

        Args:
            rank: The hand rank (lower is better)
            tiebreakers: List of tiebreaker values (higher is better)
            description: Text description of the hand
        """
        self._rank = (rank, tiebreakers, description)

    def configure_for_test(
        self,
        cards: Optional[List[Card]] = None,
        rank: Optional[int] = None,
        tiebreakers: Optional[List[int]] = None,
        description: Optional[str] = None,
    ) -> None:
        """Configure the mock hand for testing with a single method.

        Args:
            cards: Optional list of cards to set
            rank: Optional rank to set
            tiebreakers: Optional tiebreakers to set
            description: Optional description to set
        """
        if cards is not None:
            self.cards = cards

        if all(x is not None for x in [rank, tiebreakers, description]):
            self.set_rank(rank, tiebreakers, description)

    def _get_rank(self) -> tuple:
        """Get the configured rank or return default invalid hand rank."""
        if self._rank is None:
            if not self.cards:
                return (float("inf"), [], "No cards")
            if len(self.cards) != 5:
                return (float("inf"), [], "Invalid number of cards")
            return (float("inf"), [], "Invalid hand")
        return self._rank

    def __lt__(self, other: "MockHand") -> bool:
        """Compare hands using poker rankings (lower rank is better)."""
        self_rank, self_tiebreakers, _ = self._get_rank()
        other_rank, other_tiebreakers, _ = other._get_rank()

        if self_rank != other_rank:
            return self_rank > other_rank

        for self_value, other_value in zip(self_tiebreakers, other_tiebreakers):
            if self_value != other_value:
                return self_value < other_value

        return False

    def __gt__(self, other: "MockHand") -> bool:
        """Compare hands using poker rankings (lower rank is better)."""
        self_rank, self_tiebreakers, _ = self._get_rank()
        other_rank, other_tiebreakers, _ = other._get_rank()

        if self_rank != other_rank:
            return self_rank < other_rank

        return self_tiebreakers > other_tiebreakers

    def __eq__(self, other: object) -> bool:
        """Check if hands are exactly equal in rank and tiebreakers."""
        if not isinstance(other, MockHand):
            return NotImplemented
        self_rank, self_tiebreakers, _ = self._get_rank()
        other_rank, other_tiebreakers, _ = other._get_rank()
        return self_rank == other_rank and self_tiebreakers == other_tiebreakers

    def __hash__(self) -> int:
        """Hash based on cards in hand."""
        return hash(tuple(self.cards))

    def show(self) -> str:
        """Get a detailed string representation of the hand."""
        if not self.cards:
            return "Empty hand"

        cards_str = ", ".join(str(card) for card in self.cards)
        rank, tiebreakers, description = self._get_rank()
        eval_details = f"[Rank: {rank}, Tiebreakers: {tiebreakers}]"

        return f"{cards_str}\n    - {description} {eval_details}"

    def get_state(self) -> HandState:
        """Get the current state of the hand."""
        if not self.cards:
            return HandState(cards=[])

        rank_info = self._get_rank()

        return HandState(
            cards=[str(card) for card in self.cards],
            rank=rank_info[2],  # Description
            rank_value=rank_info[0],  # Numerical rank
            tiebreakers=list(rank_info[1]),  # Tiebreakers
            is_evaluated=self._rank is not None,
        )
