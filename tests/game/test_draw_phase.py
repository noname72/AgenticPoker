import logging
from unittest.mock import MagicMock, patch

import pytest

from game.draw_phase import handle_draw_phase
from game.player import Player
from game.deck import Deck
from game.hand import Hand
from game.card import Card


@pytest.fixture
def mock_players():
    """Create a list of mock players for testing."""
    players = []
    for i in range(3):
        player = Player(f"Player{i}", 1000)
        player.hand = Hand()
        player.hand.add_cards([
            Card(rank, "Hearts") 
            for rank in range(2, 7)
        ])
        player.folded = False
        players.append(player)
    return players


@pytest.fixture
def mock_deck():
    """Create a mock deck for testing."""
    deck = Deck()
    # Ensure specific cards for testing
    deck.cards = [Card(rank, "Spades") for rank in range(7, 12)]
    return deck


def test_handle_draw_phase_no_discards(mock_players, mock_deck, caplog):
    """Test draw phase when no players discard cards."""
    caplog.set_level(logging.INFO)
    
    # None of the players have decide_draw method
    handle_draw_phase(mock_players, mock_deck)
    
    # Check that all players kept their original hands
    for player in mock_players:
        assert len(player.hand.cards) == 5
        assert all(card.suit == "Hearts" for card in player.hand.cards)
        assert "Keeping current hand" in caplog.text


def test_handle_draw_phase_with_discards(mock_players, mock_deck, caplog):
    """Test draw phase when a player discards cards."""
    caplog.set_level(logging.INFO)
    
    # Set up specific cards in deck for testing
    mock_deck.cards = [Card(suit="Spades", rank="2")]
    
    # Add decide_draw method to first player
    mock_players[0].decide_draw = MagicMock(return_value=[0])  # Discard first card
    
    handle_draw_phase(mock_players, mock_deck)
    
    # Check first player's hand was modified
    assert mock_players[0].hand.cards[0].suit == "Spades"
    assert all(card.suit == "Hearts" for card in mock_players[0].hand.cards[1:])
    
    # Check other players' hands remained unchanged
    for player in mock_players[1:]:
        assert len(player.hand.cards) == 5
        assert all(card.suit == "Hearts" for card in player.hand.cards)


def test_handle_draw_phase_reshuffle(mock_players, mock_deck, caplog):
    """Test draw phase when deck needs reshuffling."""
    caplog.set_level(logging.INFO)
    
    # Set up a nearly empty deck
    mock_deck.cards = [Card(suit="Spades", rank="2")]
    
    # Add decide_draw method to first player
    mock_players[0].decide_draw = MagicMock(return_value=[0, 1, 2])  # Discard three cards
    
    handle_draw_phase(mock_players, mock_deck)
    
    assert "Reshuffling discarded cards into deck" in caplog.text
    assert len(mock_players[0].hand.cards) == 5  # Player still gets their cards


def test_handle_draw_phase_folded_players(mock_players, mock_deck):
    """Test draw phase skips folded players."""
    # Make second player folded
    mock_players[1].folded = True
    mock_players[1].decide_draw = MagicMock()  # Should never be called
    
    handle_draw_phase(mock_players, mock_deck)
    
    mock_players[1].decide_draw.assert_not_called()


def test_handle_draw_phase_no_discard_decision(mock_players, mock_deck, caplog):
    """Test draw phase when player decides not to discard."""
    caplog.set_level(logging.INFO)
    
    # Add decide_draw method that returns empty list
    mock_players[0].decide_draw = MagicMock(return_value=[])
    original_hand = mock_players[0].hand.cards.copy()
    
    handle_draw_phase(mock_players, mock_deck)
    
    assert mock_players[0].hand.cards == original_hand
    assert "Keeping current hand" in caplog.text


def test_handle_draw_phase_multiple_discards(mock_players, mock_deck):
    """Test draw phase with multiple players discarding."""
    # Set up specific cards in deck
    mock_deck.cards = [
        Card(suit="Spades", rank=str(r)) for r in range(2, 5)
    ]
    
    # Set up discards for two players
    mock_players[0].decide_draw = MagicMock(return_value=[0])
    mock_players[1].decide_draw = MagicMock(return_value=[1, 2])
    
    handle_draw_phase(mock_players, mock_deck)
    
    # Check both players got correct number of new cards
    assert len(mock_players[0].hand.cards) == 5
    assert len(mock_players[1].hand.cards) == 5
    assert mock_players[0].hand.cards[0].suit == "Spades"
    assert mock_players[1].hand.cards[1].suit == "Spades"
    assert mock_players[1].hand.cards[2].suit == "Spades" 