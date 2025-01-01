import logging
from unittest.mock import MagicMock, patch

import pytest

from game.post_draw import (
    handle_post_draw_betting,
    handle_showdown,
    _evaluate_hands,
    _log_chip_movements,
)
from game.player import Player
from game.hand import Hand
from game.types import SidePot


@pytest.fixture
def mock_players():
    """Create a list of mock players for testing."""
    players = []
    for i in range(3):
        player = Player(f"Player{i}", 1000)
        player.hand = MagicMock()
        player.folded = False
        players.append(player)
    return players


@pytest.fixture
def mock_game_state(mock_players):
    """Create a mock game state dictionary."""
    return {
        "pot": 100,
        "current_bet": 20,
        "players": [
            {
                "name": p.name,
                "chips": p.chips,
                "bet": p.bet,
                "folded": p.folded,
                "position": i,
            }
            for i, p in enumerate(mock_players)
        ],
    }


def test_handle_post_draw_betting_simple_case(mock_players, mock_game_state):
    """Test post-draw betting with a simple case (no side pots)."""
    mock_pot_manager = MagicMock()
    
    with patch("game.betting.betting_round") as mock_betting:
        mock_betting.return_value = 150  # Simple pot increase
        
        new_pot, side_pots = handle_post_draw_betting(
            mock_players,
            100,
            mock_game_state,
            mock_pot_manager
        )
        
        assert new_pot == 150
        assert side_pots is None
        mock_betting.assert_called_once_with(mock_players, 100, mock_game_state)


def test_handle_post_draw_betting_with_side_pots(mock_players, mock_game_state):
    """Test post-draw betting when side pots are created."""
    mock_pot_manager = MagicMock()
    mock_side_pots = [SidePot(amount=50, eligible_players=mock_players[:2])]
    
    with patch("game.betting.betting_round") as mock_betting:
        mock_betting.return_value = (150, mock_side_pots)
        
        new_pot, side_pots = handle_post_draw_betting(
            mock_players,
            100,
            mock_game_state,
            mock_pot_manager
        )
        
        assert new_pot == 150
        assert side_pots == mock_side_pots


def test_handle_showdown_single_winner(mock_players, caplog):
    """Test showdown with a single remaining player."""
    caplog.set_level(logging.INFO)
    mock_players[1].folded = True
    mock_players[2].folded = True
    initial_chips = {p: p.chips for p in mock_players}
    pot = 300

    handle_showdown(mock_players, pot, initial_chips)

    assert mock_players[0].chips == 1300  # Initial 1000 + pot 300
    assert "wins $300 (all others folded)" in caplog.text


def test_handle_showdown_multiple_winners(mock_players, caplog):
    """Test showdown with multiple players and split pot."""
    caplog.set_level(logging.INFO)
    initial_chips = {p: 1000 for p in mock_players}
    pot = 300

    # Mock hands to create a tie
    with patch("game.post_draw._evaluate_hands") as mock_evaluate:
        mock_evaluate.return_value = mock_players[:2]  # First two players tie
        
        handle_showdown(mock_players, pot, initial_chips)
        
        # Each winner should get half the pot (150 each)
        assert mock_players[0].chips == 1150
        assert mock_players[1].chips == 1150
        assert mock_players[2].chips == 1000
        assert "wins $150" in caplog.text


def test_evaluate_hands_single_winner():
    """Test hand evaluation with a clear winner."""
    players = []
    for i in range(3):
        player = Player(f"Player{i}", 1000)
        player.hand = MagicMock()
        players.append(player)
    
    # Set up hand comparisons
    players[0].hand.compare_to = lambda x: 1  # Better than others
    players[1].hand.compare_to = lambda x: -1  # Worse than player 0
    players[2].hand.compare_to = lambda x: -1  # Worse than player 0
    
    winners = _evaluate_hands(players)
    assert len(winners) == 1
    assert winners[0] == players[0]


def test_evaluate_hands_tie():
    """Test hand evaluation with tied winners."""
    players = []
    for i in range(3):
        player = Player(f"Player{i}", 1000)
        player.hand = MagicMock()
        players.append(player)
    
    # Set up hand comparisons for a tie
    def compare_to(other):
        return 0  # All hands tie
    
    for player in players:
        player.hand.compare_to = compare_to
    
    winners = _evaluate_hands(players)
    assert len(winners) == 3
    assert set(winners) == set(players)


def test_log_chip_movements(mock_players, caplog):
    """Test logging of chip movements."""
    caplog.set_level(logging.INFO)
    
    # Set up initial and final chip counts
    initial_chips = {
        mock_players[0]: 1000,
        mock_players[1]: 1000,
        mock_players[2]: 1000,
    }
    
    # Modify current chips to simulate wins/losses
    mock_players[0].chips = 1200  # Won 200
    mock_players[1].chips = 800   # Lost 200
    mock_players[2].chips = 1000  # No change
    
    _log_chip_movements(mock_players, initial_chips)
    
    # Check log messages
    assert "Player0: $1000 → $1200 (+200)" in caplog.text
    assert "Player1: $1000 → $800 (-200)" in caplog.text
    assert "Player2" not in caplog.text  # No change, shouldn't be logged


def test_handle_showdown_odd_chips(mock_players, caplog):
    """Test showdown with odd number of chips to split."""
    caplog.set_level(logging.INFO)
    initial_chips = {p: 1000 for p in mock_players}
    pot = 301  # Odd number

    # Mock hands to create a tie
    with patch("game.post_draw._evaluate_hands") as mock_evaluate:
        mock_evaluate.return_value = mock_players[:2]  # First two players tie
        
        handle_showdown(mock_players, pot, initial_chips)
        
        # First player should get 151, second player 150
        assert mock_players[0].chips == 1151
        assert mock_players[1].chips == 1150
        assert mock_players[2].chips == 1000 