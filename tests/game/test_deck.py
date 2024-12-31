import pytest

from game.deck import Deck


class TestDeck:
    def test_deck_initialization(self):
        """Test that a new deck has 52 cards and empty dealt/discard piles."""
        deck = Deck()
        assert len(deck.cards) == 52
        assert len(deck.dealt_cards) == 0
        assert len(deck.discarded_cards) == 0

    def test_deck_contains_all_combinations(self):
        """Test that deck contains all possible rank and suit combinations."""
        deck = Deck()
        for suit in Deck.suits:
            for rank in Deck.ranks:
                # Find at least one card with this rank and suit
                matching_cards = [
                    card
                    for card in deck.cards
                    if card.rank == rank and card.suit == suit
                ]
                assert len(matching_cards) == 1

    def test_shuffle_maintains_count(self):
        """Test that shuffling doesn't change the number of cards."""
        deck = Deck()
        initial_count = len(deck.cards)
        deck.shuffle()
        assert len(deck.cards) == initial_count

    def test_deal_single_card(self):
        """Test dealing a single card."""
        deck = Deck()
        initial_count = len(deck.cards)
        dealt_cards = deck.deal()

        assert len(dealt_cards) == 1
        assert len(deck.cards) == initial_count - 1
        assert len(deck.dealt_cards) == 1
        assert dealt_cards[0] in deck.dealt_cards

    def test_deal_multiple_cards(self):
        """Test dealing multiple cards."""
        deck = Deck()
        initial_count = len(deck.cards)
        num_cards = 5
        dealt_cards = deck.deal(num_cards)

        assert len(dealt_cards) == num_cards
        assert len(deck.cards) == initial_count - num_cards
        assert len(deck.dealt_cards) == num_cards
        for card in dealt_cards:
            assert card in deck.dealt_cards

    def test_deal_too_many_cards(self):
        """Test that dealing too many cards raises ValueError."""
        deck = Deck()
        with pytest.raises(ValueError):
            deck.deal(53)

    def test_add_discarded(self):
        """Test adding cards to discard pile."""
        deck = Deck()
        cards_to_discard = deck.deal(3)
        deck.add_discarded(cards_to_discard)

        assert len(deck.discarded_cards) == 3
        for card in cards_to_discard:
            assert card in deck.discarded_cards

    def test_reshuffle_discards(self):
        """Test reshuffling discarded cards back into deck."""
        deck = Deck()
        initial_count = len(deck.cards)

        # Deal and discard some cards
        cards_to_discard = deck.deal(3)
        deck.add_discarded(cards_to_discard)

        # Verify state before reshuffling
        assert len(deck.cards) == initial_count - 3
        assert len(deck.discarded_cards) == 3

        # Reshuffle discards
        deck.reshuffle_discards()

        # Verify state after reshuffling
        assert len(deck.cards) == initial_count - 3 + 3  # Original - dealt + discarded
        assert len(deck.discarded_cards) == 0

    def test_remaining_count(self):
        """Test the remaining() method returns correct count."""
        deck = Deck()
        assert deck.remaining() == 52

        deck.deal(5)
        assert deck.remaining() == 47

    def test_str_representation(self):
        """Test the string representation of the deck."""
        deck = Deck()
        deck.deal(2)
        deck.add_discarded(deck.dealt_cards[:1])

        expected = "Deck: 50 cards remaining, 2 dealt, 1 discarded"
        assert str(deck) == expected
