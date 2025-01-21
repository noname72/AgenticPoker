import logging
from unittest.mock import MagicMock

import pytest

from game.card import Card
from game.draw import handle_draw_phase


@pytest.fixture
def setup_mock_hands(mock_game):
    """Setup mock hands with initial cards for all players."""
    for player in mock_game.players:
        player.hand.cards = [Card(rank=str(i), suit="♥") for i in range(2, 7)]
    return mock_game


def test_handle_draw_phase_no_discards(setup_mock_hands, caplog):
    """Test draw phase when no players discard cards."""
    caplog.set_level(logging.INFO)

    # None of the players have decide_draw method
    handle_draw_phase(setup_mock_hands)

    # Check that all players kept their original hands
    for player in setup_mock_hands.players:
        assert len(player.hand.cards) == 5
        assert all(card.suit == "♥" for card in player.hand.cards)
        assert "Non-AI player or player without decision method" in caplog.text


def test_handle_draw_phase_with_discards(setup_mock_hands, caplog):
    """Test draw phase when a player discards cards."""
    caplog.set_level(logging.INFO)

    # Set up specific cards in deck for testing
    setup_mock_hands.deck.cards = [Card(rank="2", suit="♠")]

    # Add decide_draw method to first player
    setup_mock_hands.players[0].decide_discard = MagicMock(
        return_value=MagicMock(discard=[0])
    )  # Discard first card

    handle_draw_phase(setup_mock_hands)

    # Check first player's hand was modified
    assert len(setup_mock_hands.players[0].hand.cards) == 5
    assert setup_mock_hands.players[0].hand.cards[-1].suit == "♠"
    assert all(card.suit == "♥" for card in setup_mock_hands.players[0].hand.cards[:-1])

    # Check other players' hands remained unchanged
    for player in setup_mock_hands.players[1:]:
        assert len(player.hand.cards) == 5
        assert all(card.suit == "♥" for card in player.hand.cards)


def test_handle_draw_phase_reshuffle(setup_mock_hands, caplog):
    """Test draw phase when deck needs reshuffling."""
    caplog.set_level(logging.INFO)

    # Empty the deck except for one card
    setup_mock_hands.deck.cards = [Card(rank="2", suit="♠")]

    # Configure deck mock behavior
    setup_mock_hands.deck.needs_reshuffle = MagicMock(return_value=True)
    setup_mock_hands.deck.remaining_cards = MagicMock(return_value=1)
    setup_mock_hands.deck.reshuffle_all = MagicMock()

    # Configure deck to return cards after reshuffle
    def mock_deal(count):
        return [Card(rank=str(i), suit="♠") for i in range(2, 2 + count)]

    setup_mock_hands.deck.deal = MagicMock(side_effect=mock_deal)

    # Add decide_draw method to first player to discard 3 cards
    setup_mock_hands.players[0].decide_discard = MagicMock(
        return_value=MagicMock(discard=[0, 1, 2])
    )
    original_cards = setup_mock_hands.players[0].hand.cards.copy()

    handle_draw_phase(setup_mock_hands)

    # Verify reshuffle behavior with new message format
    assert (
        "Deck low on cards (1 remaining). Need 3 cards. Reshuffling..." in caplog.text
    )
    assert len(setup_mock_hands.players[0].hand.cards) == 5

    # After reshuffling, we can only verify:
    # 1. The number of cards is correct
    # 2. Some of the original cards are still in the hand
    # 3. At least one card from the deck was used

    # Check that at least one Spades card was drawn
    spades_count = sum(
        1 for card in setup_mock_hands.players[0].hand.cards if card.suit == "♠"
    )
    assert spades_count > 0, "Should have drawn at least one card from the deck"

    # Check that some original Hearts cards remain
    hearts_count = sum(
        1 for card in setup_mock_hands.players[0].hand.cards if card.suit == "♥"
    )
    assert hearts_count > 0, "Should have kept some original Hearts cards"

    # Verify total cards is still correct
    assert hearts_count + spades_count == 5, "Total cards should be 5"


def test_handle_draw_phase_folded_players(setup_mock_hands):
    """Test draw phase skips folded players."""
    # Make second player folded
    setup_mock_hands.players[1].folded = True
    setup_mock_hands.players[1].decide_discard = MagicMock()  # Should never be called

    handle_draw_phase(setup_mock_hands)

    setup_mock_hands.players[1].decide_discard.assert_not_called()


def test_handle_draw_phase_no_discard_decision(setup_mock_hands, caplog):
    """Test draw phase when player decides not to discard."""
    caplog.set_level(logging.INFO)

    # Add decide_draw method that returns empty list
    setup_mock_hands.players[0].decide_discard = MagicMock(
        return_value=MagicMock(discard=[])
    )
    original_hand = setup_mock_hands.players[0].hand.cards.copy()

    handle_draw_phase(setup_mock_hands)

    assert setup_mock_hands.players[0].hand.cards == original_hand
    assert "No cards discarded; keeping current hand" in caplog.text


def test_handle_draw_phase_multiple_discards(setup_mock_hands, caplog):
    """Test draw phase with multiple players discarding."""
    caplog.set_level(logging.DEBUG)

    # Create enough cards to avoid reshuffle
    new_cards = [Card(rank=str(r), suit="♠") for r in range(2, 12)]  # 10 cards
    setup_mock_hands.deck.cards = new_cards.copy()

    # Configure deck to return specific cards when dealing
    dealt_cards = []

    def mock_deal(count):
        nonlocal dealt_cards
        cards = [
            Card(rank=str(i), suit="♠")
            for i in range(len(dealt_cards) + 2, len(dealt_cards) + 2 + count)
        ]
        dealt_cards.extend(cards)
        return cards

    setup_mock_hands.deck.deal = MagicMock(side_effect=mock_deal)

    logging.debug(
        f"Deck cards before draw: {[str(c) for c in setup_mock_hands.deck.cards]}"
    )

    # Set up discards for two players
    setup_mock_hands.players[0].decide_discard = MagicMock(
        return_value=MagicMock(discard=[0])
    )
    setup_mock_hands.players[1].decide_discard = MagicMock(
        return_value=MagicMock(discard=[1, 2])
    )

    # Store original cards that won't be discarded
    player0_kept = setup_mock_hands.players[0].hand.cards[1:].copy()
    player1_kept = [
        setup_mock_hands.players[1].hand.cards[0]
    ] + setup_mock_hands.players[1].hand.cards[3:].copy()

    logging.debug(
        f"Player 0 original hand: {[str(c) for c in setup_mock_hands.players[0].hand.cards]}"
    )
    logging.debug(
        f"Player 1 original hand: {[str(c) for c in setup_mock_hands.players[1].hand.cards]}"
    )

    handle_draw_phase(setup_mock_hands)

    logging.debug(
        f"Player 0 final hand: {[str(c) for c in setup_mock_hands.players[0].hand.cards]}"
    )
    logging.debug(
        f"Player 1 final hand: {[str(c) for c in setup_mock_hands.players[1].hand.cards]}"
    )
    logging.debug(
        f"Deck cards after draw: {[str(c) for c in setup_mock_hands.deck.cards]}"
    )

    # Check first player's hand
    assert len(setup_mock_hands.players[0].hand.cards) == 5
    assert (
        setup_mock_hands.players[0].hand.cards[:-1] == player0_kept
    )  # First 4 cards unchanged
    assert (
        setup_mock_hands.players[0].hand.cards[-1].suit == "♠"
    )  # New card should be a Spade

    # Check second player's hand
    assert len(setup_mock_hands.players[1].hand.cards) == 5
    assert (
        setup_mock_hands.players[1].hand.cards[0] == player1_kept[0]
    )  # First card unchanged
    assert (
        setup_mock_hands.players[1].hand.cards[1] == player1_kept[1]
    )  # Second card unchanged
    assert all(
        card.suit == "♠" for card in setup_mock_hands.players[1].hand.cards[-2:]
    )  # Last two cards should be Spades


def test_handle_draw_phase_negative_index(setup_mock_hands, caplog):
    """Test draw phase when player provides negative discard indexes."""
    caplog.set_level(logging.INFO)

    # Add decide_draw method that returns negative index
    setup_mock_hands.players[0].decide_discard = MagicMock(
        return_value=MagicMock(discard=[-1])
    )
    original_hand = setup_mock_hands.players[0].hand.cards.copy()

    handle_draw_phase(setup_mock_hands)

    # Check that hand remained unchanged
    assert setup_mock_hands.players[0].hand.cards == original_hand
    assert "invalid discard indexes" in caplog.text
    assert f"{setup_mock_hands.players[0].name} keeping current hand" in caplog.text


def test_draw_phase_logging_not_duplicated(setup_mock_hands, caplog):
    """Test that draw phase logging isn't duplicated."""
    caplog.set_level(logging.INFO)

    # Set up a player with discards
    setup_mock_hands.players[0].decide_discard = MagicMock(
        return_value=MagicMock(discard=[0, 1])
    )

    handle_draw_phase(setup_mock_hands)

    # Count occurrences of discard logging for this player
    discard_logs = sum(
        1
        for record in caplog.records
        if f"Draw phase: {setup_mock_hands.players[0].name} discarding"
        in record.message
    )

    assert discard_logs == 1, "Discard action should only be logged once"
