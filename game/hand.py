from typing import List, Optional, Tuple

from data.types.hand_rank import HandRank
from data.types.hand_types import HandState

from .card import Card
from .evaluator import evaluate_hand


class Hand:
    """
    Represents a poker hand with comparison capabilities based on poker hand rankings.

    Supports standard poker hand comparisons, card management, and evaluation caching
    for performance. Hands are compared using standard poker rankings where lower
    rank numbers indicate better hands (1 is best).

    Attributes:
        cards (List[Card]): List of cards currently in the hand
        _rank (Optional[tuple]): Cached evaluation result (rank, tiebreakers, description)
    """

    def __init__(self, cards: Optional[List[Card]] = None) -> None:
        """
        Initialize a hand, optionally with a starting set of cards.

        Args:
            cards: Optional list of cards to initialize the hand with. Defaults to empty list.
        """
        self.cards = cards if cards is not None else []
        self._rank: Optional[tuple] = None

    def __lt__(self, other: "Hand") -> bool:
        """Compare if this hand ranks lower than another hand."""
        return self.compare_to(other) < 0

    def __gt__(self, other: "Hand") -> bool:
        """Compare if this hand ranks higher than another hand."""
        return self.compare_to(other) > 0

    def __eq__(self, other: "Hand") -> bool:
        """Check if hands are exactly equal in rank and tiebreakers."""
        return self.compare_to(other) == 0

    def _get_rank(self) -> tuple:
        """Get the cached rank or calculate and cache it if needed."""
        if self._rank is None:
            if not self.cards:
                return (
                    float("inf"),
                    [],
                    "Empty hand",
                )  # Use consistent "Empty hand" message
            if len(self.cards) != 5:
                return (float("inf"), [], "Invalid number of cards")
            try:
                self._rank = self.evaluate()
            except (ValueError, KeyError) as e:
                return (float("inf"), [], f"Invalid hand: {str(e)}")
        return self._rank or (float("inf"), [], "Empty hand")

    def add_cards(self, cards: List[Card]) -> None:
        """Add cards to the hand and invalidate the cached rank."""
        if cards is None:
            raise TypeError("Cannot add None as cards")
        if not isinstance(cards, list):
            raise TypeError("Cards must be provided as a list")
        if any(not isinstance(card, Card) for card in cards):
            raise TypeError("All elements must be Card objects")
        self.cards.extend(cards)
        self._rank = None  # Invalidate cached rank

    def remove_cards(self, positions: List[int]) -> None:
        """
        Remove cards from the hand by index positions (highest first),
        then invalidate the cached rank.
        """
        for idx in sorted(positions, reverse=True):
            self.cards.pop(idx)
        self._rank = None

    def show(self) -> str:
        """
        Get a detailed string representation of the hand.

        Returns:
            str: Multi-line string containing:
                - Comma-separated list of cards
                - Hand ranking description
                - Technical evaluation details (rank and tiebreakers)
        """
        if not self.cards:
            return "Empty hand"

        cards_str = ", ".join(str(card) for card in self.cards)

        # Always use evaluate() for valid hands to ensure consistent evaluation
        if len(self.cards) == 5:
            try:
                rank, tiebreakers, description = self.evaluate()
            except (ValueError, KeyError):
                rank, tiebreakers, description = float("inf"), [], "Invalid hand"
        else:
            rank, tiebreakers, description = float("inf"), [], "Invalid number of cards"

        # Create detailed evaluation string without Unicode characters
        eval_details = f"[Rank: {rank}, Tiebreakers: {tiebreakers}]"

        return f"{cards_str}\n    - {description} {eval_details}"

    def evaluate(self) -> Tuple[int, List[int], str]:
        """Evaluate the current hand and return its ranking information."""
        if not self.cards or len(self.cards) != 5:
            raise ValueError("Cannot evaluate hand: incorrect number of cards")

        return evaluate_hand(self.cards)

    def get_state(self) -> HandState:
        """Get the current state of the hand."""
        if not self.cards:
            return HandState(cards=[])

        # Get evaluation if needed
        if self._rank is None and len(self.cards) == 5:
            self._rank = self.evaluate()

        return HandState(
            cards=[str(card) for card in self.cards],
            rank=self._rank[2] if self._rank else None,  # Description
            rank_value=self._rank[0] if self._rank else None,  # Numerical rank
            tiebreakers=list(self._rank[1]) if self._rank else [],  # Tiebreakers
            is_evaluated=self._rank is not None,
        )

    def compare_to(self, other: "Hand") -> int:
        """Compare this hand to another hand.

        Returns:
            int: Positive if this hand is better, negative if worse, 0 if equal
        """
        # Get ranks for both hands using _get_rank to handle invalid cases
        self_rank, self_tiebreakers, _ = self._get_rank()
        other_rank, other_tiebreakers, _ = other._get_rank()

        # If both hands are invalid (infinite rank), they're equal
        if self_rank == float("inf") and other_rank == float("inf"):
            return 0

        # If one hand is invalid, it loses
        if self_rank == float("inf"):
            return -1
        if other_rank == float("inf"):
            return 1

        # Compare ranks using enum values
        if self_rank != other_rank:
            # Convert to values for comparison, higher value is better
            return self_rank.value - other_rank.value

        # If ranks are equal, compare tiebreakers (higher is better)
        for self_value, other_value in zip(self_tiebreakers, other_tiebreakers):
            if self_value != other_value:
                return self_value - other_value

        return 0  # Hands are equal

    def get_rank(self) -> HandRank:
        """
        Evaluate the hand and return its rank.

        Returns:
            HandRank: The rank of this hand from HIGH_CARD to ROYAL_FLUSH
        """
        if self._is_royal_flush():
            return HandRank.ROYAL_FLUSH
        elif self._is_straight_flush():
            return HandRank.STRAIGHT_FLUSH
        elif self._is_four_of_kind():
            return HandRank.FOUR_OF_KIND
        elif self._is_full_house():
            return HandRank.FULL_HOUSE
        elif self._is_flush():
            return HandRank.FLUSH
        elif self._is_straight():
            return HandRank.STRAIGHT
        elif self._is_three_of_kind():
            return HandRank.THREE_OF_KIND
        elif self._is_two_pair():
            return HandRank.TWO_PAIR
        elif self._is_one_pair():
            return HandRank.ONE_PAIR
        else:
            return HandRank.HIGH_CARD
