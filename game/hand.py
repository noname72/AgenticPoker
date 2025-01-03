from typing import List, Optional, Tuple

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
        """
        Compare if this hand ranks lower than another hand.

        Args:
            other: Hand to compare against

        Returns:
            bool: True if this hand ranks lower than the other hand

        Note:
            Compares primary rank first (lower is better), then tiebreakers.
            For tiebreakers, higher values are better (opposite of primary rank).
        """
        self_rank, self_tiebreakers, _ = self._get_rank()
        other_rank, other_tiebreakers, _ = other._get_rank()

        # First compare primary ranks (lower is better)
        if self_rank != other_rank:
            return self_rank > other_rank

        # If ranks are equal, compare each tiebreaker (higher is better)
        for self_value, other_value in zip(self_tiebreakers, other_tiebreakers):
            if self_value != other_value:
                return self_value < other_value

        return False  # Equal hands

    def __gt__(self, other: "Hand") -> bool:
        """Compare hands using poker rankings."""
        self_rank, self_tiebreakers, _ = self._get_rank()
        other_rank, other_tiebreakers, _ = other._get_rank()

        if self_rank != other_rank:
            return self_rank < other_rank  # Lower rank numbers are better

        # If ranks are equal, compare tiebreakers in order
        return self_tiebreakers > other_tiebreakers

    def __eq__(self, other: "Hand") -> bool:
        """Check if hands are exactly equal in rank and tiebreakers."""
        self_rank, self_tiebreakers, _ = self._get_rank()
        other_rank, other_tiebreakers, _ = other._get_rank()
        return self_rank == other_rank and self_tiebreakers == other_tiebreakers

    def _get_rank(self) -> tuple:
        """Get the cached rank or calculate and cache it if needed."""
        if self._rank is None:
            if not self.cards:
                return (float("inf"), [], "No cards")
            if len(self.cards) != 5:
                return (float("inf"), [], "Invalid number of cards")
            try:
                self._rank = evaluate_hand(self.cards)
            except (ValueError, KeyError):
                return (float("inf"), [], "Invalid hand")
        return self._rank or (float("inf"), [], "No cards")

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
        rank, tiebreakers, description = self._get_rank()

        # Create detailed evaluation string without Unicode characters
        eval_details = f"[Rank: {rank}, Tiebreakers: {tiebreakers}]"

        return f"{cards_str}\n    - {description} {eval_details}"

    def evaluate(self) -> Tuple[int, List[int], str]:
        """Evaluate the current hand and return its ranking information."""
        if not self.cards or len(self.cards) != 5:
            raise ValueError("Cannot evaluate hand: incorrect number of cards")

        return evaluate_hand(self.cards)
