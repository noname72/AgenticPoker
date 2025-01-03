import logging
from unittest.mock import MagicMock, patch

import pytest

from game.player import Player
from game.pre_draw import handle_pre_draw_betting
from game.types import SidePot


@pytest.fixture
def mock_players():
    """Create a list of mock players for testing."""
    players = []
    for i in range(3):
        player = Player(f"Player{i}", 1000)
        player.hand = MagicMock()
        player.folded = False
        player.bet = 0
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
        "dealer_index": 0,
    }


def test_handle_pre_draw_betting_simple_case(mock_players, mock_game_state):
    """Test pre-draw betting with a simple case (no side pots)."""
    # Mock player decisions
    for player in mock_players:
        player.decide_action = lambda x: ("call", 20)

    new_pot, side_pots, should_continue = handle_pre_draw_betting(
        players=mock_players,
        pot=100,
        dealer_index=0,
        game_state=mock_game_state,
    )

    assert new_pot == 160  # Initial 100 + (20 * 3)
    assert side_pots is None
    assert should_continue is True
    assert all(p.bet == 20 for p in mock_players)


def test_handle_pre_draw_betting_with_raises(mock_players, mock_game_state):
    """Test pre-draw betting with raises."""
    # Setup player decisions
    mock_players[0].decide_action = lambda x: ("raise", 40)  # First player raises
    mock_players[1].decide_action = lambda x: ("call", 40)  # Second player calls
    mock_players[2].decide_action = lambda x: ("fold", 0)  # Third player folds

    new_pot, side_pots, should_continue = handle_pre_draw_betting(
        players=mock_players,
        pot=100,
        dealer_index=0,
        game_state=mock_game_state,
    )

    assert new_pot == 180  # Initial 100 + (40 * 2)
    assert side_pots is None
    assert should_continue is True
    assert mock_players[0].bet == 40
    assert mock_players[1].bet == 40
    assert mock_players[2].folded is True


def test_handle_pre_draw_betting_all_fold(mock_players, mock_game_state):
    """Test pre-draw betting when all but one player folds."""
    # Setup player decisions
    mock_players[0].decide_action = lambda x: ("raise", 40)
    mock_players[1].decide_action = lambda x: ("fold", 0)
    mock_players[2].decide_action = lambda x: ("fold", 0)

    new_pot, side_pots, should_continue = handle_pre_draw_betting(
        players=mock_players,
        pot=100,
        dealer_index=0,
        game_state=mock_game_state,
    )

    assert new_pot == 140  # Initial 100 + 40
    assert side_pots is None
    assert should_continue is False  # Game should not continue
    assert mock_players[0].bet == 40
    assert all(p.folded for p in mock_players[1:])


def test_handle_pre_draw_betting_all_in(mock_players, mock_game_state):
    """Test pre-draw betting with all-in situations."""
    # Setup players with different chip amounts
    mock_players[0].chips = 500
    mock_players[1].chips = 300
    mock_players[2].chips = 100

    # Setup player decisions
    mock_players[0].decide_action = lambda x: ("raise", 500)
    mock_players[1].decide_action = lambda x: ("call", 300)
    mock_players[2].decide_action = lambda x: ("call", 100)

    new_pot, side_pots, should_continue = handle_pre_draw_betting(
        players=mock_players,
        pot=100,
        dealer_index=0,
        game_state=mock_game_state,
    )

    assert new_pot == 1000  # Initial 100 + 500 + 300 + 100
    assert side_pots is not None
    assert len(side_pots) == 3  # Three different betting levels
    assert should_continue is True


def test_handle_pre_draw_betting_invalid_actions(mock_players, mock_game_state):
    """Test handling of invalid betting actions."""
    # Setup player with invalid action
    mock_players[0].decide_action = lambda x: ("invalid", 50)
    mock_players[1].decide_action = lambda x: ("call", 20)
    mock_players[2].decide_action = lambda x: ("call", 20)

    new_pot, side_pots, should_continue = handle_pre_draw_betting(
        players=mock_players,
        pot=100,
        dealer_index=0,
        game_state=mock_game_state,
    )

    # Invalid action should be converted to call
    assert new_pot == 160  # Initial 100 + (20 * 3)
    assert side_pots is None
    assert should_continue is True
    assert all(p.bet == 20 for p in mock_players)
