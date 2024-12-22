from typing import List, Optional

from .card import Card
from .evaluator import evaluate_hand


class Hand:
    """
    Represents a poker hand with comparison capabilities based on poker hand rankings.

    Attributes:
        cards (List[Card]): List of cards in the hand
        rank (tuple): Cached evaluation result (rank, tiebreakers, description)
    """

    def __init__(self, cards: Optional[List[Card]] = None) -> None:
        """
        Initialize a hand, optionally with cards.

        Args:
            cards: Optional list of cards to start with
        """
        self.cards = cards if cards is not None else []
        self._rank: Optional[tuple] = None

    def __lt__(self, other: "Hand") -> bool:
        """Compare hands using poker rankings (lower rank numbers are better)."""
        return (
            self._get_rank()[0] > other._get_rank()[0]
        )  # Reversed because 1 is best in evaluator

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
        Get the cached rank or calculate it if needed.

        Returns:
            tuple: (rank, tiebreakers, description)
        """
        if self._rank is None and self.cards:
            self._rank = evaluate_hand(self.cards)
        return self._rank or (float("inf"), [], "No cards")

    def add_cards(self, cards: List[Card]) -> None:
        """
        Add cards to the hand and invalidate cached rank.

        Args:
            cards: List of cards to add
        """
        self.cards.extend(cards)
        self._rank = None  # Invalidate cached rank

    def show(self) -> str:
        """
        Get a string representation of the hand.

        Returns:
            str: Comma-separated list of cards and hand ranking
        """
        if not self.cards:
            return "Empty hand"
        cards_str = ", ".join(str(card) for card in self.cards)
        rank = self._get_rank()
        return f"{cards_str} ({rank[2]})"
