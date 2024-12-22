from typing import List, Optional

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
        """Compare hands using poker rankings (lower rank numbers are better)."""
        return (
            self._get_rank()[0] < other._get_rank()[0]
        )  # Reversed because 1 is best in evaluator

    def __eq__(self, other: "Hand") -> bool:
        """Check if hands are equal in rank."""
        return self._get_rank()[0] == other._get_rank()[0]

    def _get_rank(self) -> tuple:
        """
        Get the cached rank or calculate and cache it if needed.

        Returns:
            tuple: Contains (rank, tiebreakers, description) where:
                - rank: Integer ranking (lower is better)
                - tiebreakers: List of values for breaking ties
                - description: Human-readable description of the hand
        """
        if self._rank is None and self.cards:
            self._rank = evaluate_hand(self.cards)
        return self._rank or (float("inf"), [], "No cards")

    def add_cards(self, cards: List[Card]) -> None:
        """
        Add cards to the hand and invalidate the cached rank.

        Args:
            cards: List of cards to add to the hand

        Note:
            This method automatically invalidates any cached rank evaluation.
        """
        self.cards.extend(cards)
        self._rank = None  # Invalidate cached rank

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

    def evaluate(self) -> str:
        """
        Get a formatted string of the hand's evaluation details.

        Returns:
            str: String containing the numerical rank, hand description,
                and tiebreaker values used for comparison
        """
        rank, tiebreakers, description = self._get_rank()
        return f"Rank {rank} - {description} (Tiebreakers: {tiebreakers})"
