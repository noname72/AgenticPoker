import logging
import random
from typing import List

from data.types.base_types import DeckState

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
        """
        # Reset tracking lists when shuffling a fresh deck
        if len(self.cards) == 52:
            self.dealt_cards = []
            self.discarded_cards = []
        else:
            logging.info(f"Shuffling deck with {len(self.cards)} cards")

        random.shuffle(self.cards)
        self.last_action = "shuffle"

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
        self.last_action = f"deal_{num}"
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

    def remaining_cards(self) -> int:
        """Get count of remaining cards in deck."""
        return len(self.cards)

    def needs_reshuffle(self, needed_cards: int) -> bool:
        """Check if deck needs reshuffling based on needed cards."""
        return len(self.cards) < needed_cards

    def reshuffle_all(self) -> None:
        """Reshuffle ALL cards (including dealt and discarded) back into deck."""
        self.cards.extend(self.dealt_cards)
        self.cards.extend(self.discarded_cards)
        self.dealt_cards = []
        self.discarded_cards = []
        self.shuffle()
        logging.info("Full deck reshuffle - all 52 cards back in play")

    def __str__(self) -> str:
        """Return string representation of current deck state."""
        return (
            f"Deck: {len(self.cards)} cards remaining, "
            f"{len(self.dealt_cards)} dealt, "
            f"{len(self.discarded_cards)} discarded"
        )

    def get_state(self) -> DeckState:
        """Get the current state of the deck."""
        return DeckState(
            cards_remaining=len(self.cards),
            cards_dealt=len(self.dealt_cards),
            cards_discarded=len(self.discarded_cards),
            needs_shuffle=self.needs_reshuffle(
                5
            ),  # Check if we need shuffle for a 5-card deal
            last_action=getattr(self, "last_action", None),
        )
