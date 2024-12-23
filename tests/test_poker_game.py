import pytest
from unittest.mock import Mock, patch
import logging
from datetime import datetime

from game import AgenticPoker
from agents.llm_agent import LLMAgent
from data.enums import StrategyStyle, PlayerStatus, ActionType

@pytest.fixture
def mock_players():
    """Fixture to create mock players."""
    return [
        Mock(spec=LLMAgent, name="Alice", chips=1000),
        Mock(spec=LLMAgent, name="Bob", chips=1000),
        Mock(spec=LLMAgent, name="Charlie", chips=1000)
    ]

@pytest.fixture
def game(mock_players):
    """Fixture to create game instance."""
    return AgenticPoker(
        players=mock_players,
        starting_chips=1000,
        small_blind=50,
        big_blind=100,
        ante=10,
        session_id=datetime.now().strftime("%Y%m%d_%H%M%S")
    )

def test_game_initialization(game, mock_players):
    """Test game initialization with valid parameters."""
    assert len(game.players) == 3
    assert game.small_blind == 50
    assert game.big_blind == 100
    assert game.ante == 10
    assert game.session_id is not None

def test_invalid_game_initialization():
    """Test game initialization with invalid parameters."""
    with pytest.raises(ValueError):
        AgenticPoker(
            players=[],  # Empty players list
            starting_chips=1000,
            small_blind=50,
            big_blind=100
        )

    with pytest.raises(ValueError):
        AgenticPoker(
            players=mock_players,
            starting_chips=-1000,  # Negative chips
            small_blind=50,
            big_blind=100
        )

def test_betting_round(game, mock_players):
    """Test betting round mechanics."""
    # Mock player actions
    mock_players[0].get_action.return_value = ActionType.RAISE
    mock_players[1].get_action.return_value = ActionType.CALL
    mock_players[2].get_action.return_value = ActionType.FOLD

    # Start betting round
    game._handle_betting_round()

    # Verify player actions were called
    for player in mock_players:
        player.get_action.assert_called_once()

# ... Rest of the tests converted to pytest style ... 