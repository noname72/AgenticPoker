import random
from typing import List

from .card import Card


class Deck:
    """A standard 52-card deck with tracking of dealt and discarded cards."""

    ranks = [2, 3, 4, 5, 6, 7, 8, 9, 10, "J", "Q", "K", "A"]
    suits = ["♣", "♦", "♥", "♠"]  # Using Unicode symbols for better readability

    def __init__(self):
        """Initialize a new deck with all 52 cards."""
        self.cards = [Card(rank, suit) for suit in self.suits for rank in self.ranks]
        self.dealt_cards: List[Card] = []  # Track dealt cards
        self.discarded_cards: List[Card] = []  # Track discarded cards

    def shuffle(self) -> None:
        """
        Shuffle the current deck.

        If discarded cards exist, they can optionally be shuffled back in.
        """
        random.shuffle(self.cards)

    def deal(self, num: int = 1) -> List[Card]:
        """
        Deal a specified number of cards from the deck.

        Args:
            num: Number of cards to deal

        Returns:
            List of dealt cards

        Raises:
            ValueError: If requesting more cards than available
        """
        if num > len(self.cards):
            raise ValueError(
                f"Cannot deal {num} cards. Only {len(self.cards)} cards remaining."
            )

        dealt = self.cards[:num]
        self.cards = self.cards[num:]
        self.dealt_cards.extend(dealt)
        return dealt

    def add_discarded(self, cards: List[Card]) -> None:
        """Add discarded cards to the discard pile."""
        self.discarded_cards.extend(cards)

    def reshuffle_discards(self) -> None:
        """Shuffle discarded cards back into the deck."""
        self.cards.extend(self.discarded_cards)
        self.discarded_cards = []
        self.shuffle()

    def remaining(self) -> int:
        """Return number of cards remaining in deck."""
        return len(self.cards)

    def __str__(self) -> str:
        """Return string representation of current deck state."""
        return (
            f"Deck: {len(self.cards)} cards remaining, "
            f"{len(self.dealt_cards)} dealt, "
            f"{len(self.discarded_cards)} discarded"
        )
