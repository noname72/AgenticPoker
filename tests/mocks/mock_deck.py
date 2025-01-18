from typing import List
from unittest.mock import MagicMock

from data.types.base_types import DeckState
from game.card import Card


class MockDeck:
    """A mock implementation of the Deck class for testing purposes.

    This mock provides the same interface as the real Deck class but with configurable
    behaviors for testing. It tracks deck state and allows easy configuration of card
    dealing and shuffling behaviors.

    Usage:
        # Basic initialization
        deck = MockDeck()

        # Configure specific cards to be dealt
        test_cards = [
            Card("A", "♠"),
            Card("K", "♠"),
            Card("Q", "♠")
        ]
        deck.set_next_cards(test_cards)  # These cards will be dealt in order

        # Deal cards and verify
        dealt = deck.deal(3)
        assert dealt == test_cards
        assert deck.remaining() == 49  # 52 - 3 dealt

        # Configure shuffle behavior
        deck.simulate_shuffle()  # Reset deck to 52 cards

        # Test discarding
        deck.add_discarded([Card("A", "♠")])
        assert len(deck.discarded_cards) == 1

        # Verify method calls
        deck.deal.assert_called_with(3)
        deck.shuffle.assert_called_once()

    Default Behaviors:
        - deal: Returns configured cards or raises if insufficient cards
        - shuffle: Resets deck state
        - add_discarded: Adds cards to discard pile
        - reshuffle_discards: Returns discards to deck
        - remaining/remaining_cards: Returns count of available cards
        - needs_reshuffle: Checks if reshuffle needed based on needed cards
        - reshuffle_all: Resets entire deck state

    Attributes:
        cards (List[Card]): Current cards in deck
        dealt_cards (List[Card]): Cards that have been dealt
        discarded_cards (List[Card]): Cards in discard pile
        sample_cards (List[Card]): Preset cards for testing
        ranks (List): Standard card ranks
        suits (List): Standard card suits

    All methods are MagicMocks that can be configured with custom return values
    or side effects as needed for testing.

    Note:
        - Default initialization creates a full 52-card deck
        - Dealing cards maintains proper deck state
        - Shuffle operations properly reset relevant card collections
        - State can be manually configured for specific test scenarios
    """

    # Add class attributes to match original Deck
    ranks = [2, 3, 4, 5, 6, 7, 8, 9, 10, "J", "Q", "K", "A"]
    suits = ["♣", "♦", "♥", "♠"]

    def __init__(self):
        """Initialize a mock deck with basic tracking attributes."""
        # Initialize with a full deck of 52 cards like the original
        self.cards: List[Card] = [
            Card(rank, suit) for suit in self.suits for rank in self.ranks
        ]
        self.dealt_cards: List[Card] = []
        self.discarded_cards: List[Card] = []
        self.last_action = None

        # Create mock methods that can be configured in tests
        self.shuffle = MagicMock()
        self.deal = MagicMock(return_value=[])
        self.add_discarded = MagicMock()
        self.reshuffle_discards = MagicMock()
        self.reshuffle_all = MagicMock()

        # Set up some default cards for testing
        self._setup_default_cards()

    def _setup_default_cards(self):
        """Set up some default cards that can be used in tests."""
        # Create a few sample cards that tests might need
        self.sample_cards = [
            Card("A", "♠"),
            Card("K", "♥"),
            Card("Q", "♦"),
            Card("J", "♣"),
        ]
        # Configure default behaviors
        self.deal.return_value = self.sample_cards[:1]  # Default to dealing one card

        def mock_deal_behavior(num: int = 1) -> List[Card]:
            if num > len(self.cards):
                raise ValueError("Insufficient cards remaining")
            return self.sample_cards[:num]

        self.deal.side_effect = mock_deal_behavior

    def set_next_cards(self, cards: List[Card]) -> None:
        """Configure the next cards to be dealt in order.

        Useful for setting up specific test scenarios.

        Args:
            cards: List of cards to be dealt in order
        """
        self.deal.reset_mock()
        self.deal.side_effect = None
        self.deal.return_value = cards

    def remaining(self) -> int:
        """Return number of cards remaining in deck."""
        return len(self.cards)

    def remaining_cards(self) -> int:
        """Get count of remaining cards in deck."""
        return len(self.cards)

    def needs_reshuffle(self, needed_cards: int) -> bool:
        """Check if deck needs reshuffling based on needed cards."""
        return len(self.cards) < needed_cards

    def get_state(self) -> DeckState:
        """Get the current state of the deck."""
        return DeckState(
            cards_remaining=len(self.cards),
            cards_dealt=len(self.dealt_cards),
            cards_discarded=len(self.discarded_cards),
            needs_shuffle=self.needs_reshuffle(5),
            last_action=self.last_action,
        )

    def simulate_shuffle(self) -> None:
        """Simulate shuffling by resetting deck state.

        Useful for tests that need to verify shuffle behavior.
        """
        self.cards = [Card(rank, suit) for suit in self.suits for rank in self.ranks]
        self.dealt_cards = []
        self.discarded_cards = []
        self.last_action = "shuffle"

    def simulate_deal(self, num_cards: int) -> List[Card]:
        """Simulate dealing cards by actually modifying deck state.

        Useful for tests that need to verify deck state changes.

        Args:
            num_cards: Number of cards to deal

        Returns:
            List of dealt cards
        """
        if num_cards > len(self.cards):
            raise ValueError("Insufficient cards remaining")
        dealt = self.cards[:num_cards]
        self.cards = self.cards[num_cards:]
        self.dealt_cards.extend(dealt)
        self.last_action = f"deal_{num_cards}"
        return dealt

    def __str__(self) -> str:
        """Return string representation of current deck state."""
        return (
            f"MockDeck: {len(self.cards)} cards remaining, "
            f"{len(self.dealt_cards)} dealt, "
            f"{len(self.discarded_cards)} discarded"
        )
