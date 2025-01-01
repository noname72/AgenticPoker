import logging
from unittest.mock import MagicMock, patch

import pytest

from game.player import Player
from game.pre_draw import _log_chip_movements, handle_pre_draw_betting
from game.types import SidePot


@pytest.fixture
def mock_players():
    """Create a list of mock players for testing."""
    players = []
    for i in range(3):
        player = Player(f"Player{i}", 1000)
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


def test_handle_pre_draw_betting_all_active(mock_players, mock_game_state):
    """Test pre-draw betting when all players remain active."""
    mock_pot_manager = MagicMock()

    with patch("game.betting.handle_betting_round") as mock_betting:
        mock_betting.return_value = (150, None)

        new_pot, side_pots, should_continue = handle_pre_draw_betting(
            mock_players, 100, 0, mock_game_state, mock_pot_manager
        )

        mock_betting.assert_called_once_with(
            players=mock_players,
            pot=100,
            dealer_index=0,
            game_state=mock_game_state,
            phase="pre-draw",
        )

        assert new_pot == 150
        assert side_pots is None
        assert should_continue is True


def test_handle_pre_draw_betting_one_remaining(mock_players, mock_game_state, caplog):
    """Test pre-draw betting when all but one player folds."""
    caplog.set_level(logging.INFO)
    mock_pot_manager = MagicMock()

    # Make all but first player fold
    mock_players[1].folded = True
    mock_players[2].folded = True

    with patch("game.betting.handle_betting_round") as mock_betting:
        # Add a side pot to test total payout calculation
        mock_side_pots = [SidePot(amount=50, eligible_players=mock_players[:2])]
        mock_betting.return_value = (150, mock_side_pots)

        new_pot, side_pots, should_continue = handle_pre_draw_betting(
            mock_players, 100, 0, mock_game_state, mock_pot_manager
        )

        # Pot should be reset to 0 after awarding
        assert new_pot == 0
        assert side_pots == mock_side_pots
        assert should_continue is False
        # Player should receive main pot (150) + side pot (50)
        assert mock_players[0].chips == 1200  # Initial 1000 + total payout 200
        assert "wins $200 (all others folded pre-draw)" in caplog.text


def test_handle_pre_draw_betting_with_side_pots(mock_players, mock_game_state):
    """Test pre-draw betting with side pots."""
    mock_pot_manager = MagicMock()
    mock_side_pots = [SidePot(amount=50, eligible_players=mock_players[:2])]

    with patch("game.betting.handle_betting_round") as mock_betting:
        mock_betting.return_value = (150, mock_side_pots)

        new_pot, side_pots, should_continue = handle_pre_draw_betting(
            mock_players, 100, 0, mock_game_state, mock_pot_manager
        )

        assert new_pot == 150
        assert side_pots == mock_side_pots
        assert should_continue is True


def test_log_chip_movements(mock_players, mock_game_state, caplog):
    """Test logging of chip movements."""
    caplog.set_level(logging.INFO)

    # Modify current chips to simulate wins/losses
    mock_players[0].chips = 1200  # Won 200
    mock_players[1].chips = 800  # Lost 200
    mock_players[2].chips = 1000  # No change

    _log_chip_movements(mock_players, mock_game_state)

    # Check log messages
    assert "Player0: $1000 → $1200 (+200)" in caplog.text
    assert "Player1: $1000 → $800 (-200)" in caplog.text
    assert "Player2" not in caplog.text  # No change, shouldn't be logged


def test_handle_pre_draw_betting_all_in(mock_players, mock_game_state):
    """Test pre-draw betting with all-in situations."""
    mock_pot_manager = MagicMock()
    mock_side_pots = [
        SidePot(amount=100, eligible_players=mock_players),
        SidePot(amount=50, eligible_players=mock_players[:2]),
    ]

    # Simulate one player being all-in
    mock_players[2].chips = 0

    with patch("game.betting.handle_betting_round") as mock_betting:
        mock_betting.return_value = (150, mock_side_pots)

        new_pot, side_pots, should_continue = handle_pre_draw_betting(
            mock_players, 100, 0, mock_game_state, mock_pot_manager
        )

        assert new_pot == 150
        assert len(side_pots) == 2
        assert side_pots[0].amount == 100
        assert side_pots[1].amount == 50
        assert should_continue is True
