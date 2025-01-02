from datetime import datetime
from unittest.mock import Mock

import pytest

from agents.llm_agent import LLMAgent
from game import AgenticPoker
from game.hand import Hand


@pytest.fixture
def mock_players():
    """Fixture to create mock players."""
    players = []
    for name in ["Alice", "Bob", "Charlie"]:
        player = Mock(spec=LLMAgent)
        player.name = name
        player.chips = 1000
        player.folded = False
        player.bet = 0
        # Mock hand attribute
        player.hand = Mock(spec=Hand)
        player.hand.__eq__ = lambda self, other: False
        player.hand.__gt__ = lambda self, other: False

        # Create a proper place_bet method that updates chips
        def make_place_bet(p):
            def place_bet(amount):
                actual_amount = min(amount, p.chips)
                p.chips -= actual_amount
                p.bet += actual_amount
                return actual_amount
            return place_bet

        player.place_bet = make_place_bet(player)
        players.append(player)
    return players


@pytest.fixture
def game(mock_players):
    """Fixture to create game instance."""
    return AgenticPoker(
        players=mock_players,
        small_blind=50,
        big_blind=100,
        ante=10,
        session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
    )


def test_game_initialization(game, mock_players):
    """Test game initialization with valid parameters."""
    assert len(game.players) == 3
    assert game.small_blind == 50
    assert game.big_blind == 100
    assert game.ante == 10
    assert game.session_id is not None
    # Verify all players have initial chips
    for player in game.players:
        assert player.chips == 1000


def test_invalid_game_initialization(mock_players):
    """Test game initialization with invalid parameters."""
    with pytest.raises(ValueError):
        AgenticPoker(
            players=[],  # Empty players list
            small_blind=50,
            big_blind=100,
            ante=10,
        )

    with pytest.raises(ValueError):
        # Create players with negative chips
        invalid_players = [
            Mock(spec=LLMAgent, chips=-1000, name=f"Player{i}") for i in range(3)
        ]
        AgenticPoker(
            players=invalid_players,
            small_blind=50,
            big_blind=100,
            ante=10,
        )


def test_dealer_rotation(game, mock_players):
    """Test dealer button rotation between rounds."""
    initial_dealer = game.dealer_index
    
    # Initialize round which rotates dealer
    game._initialize_round()
    
    # Verify dealer rotated
    expected_dealer = (initial_dealer + 1) % len(mock_players)
    assert game.dealer_index == expected_dealer


def test_round_initialization(game, mock_players):
    """Test initialization of a new round."""
    game._initialize_round()
    
    # Verify round state
    assert game.pot_manager.pot == 0
    assert all(player.bet == 0 for player in game.players)
    assert all(not player.folded for player in game.players)
    assert all(hasattr(player, 'hand') for player in game.players)


def test_game_state_creation(game, mock_players):
    """Test creation of game state dictionary."""
    game_state = game._create_game_state()
    
    assert 'pot' in game_state
    assert 'players' in game_state
    assert 'current_bet' in game_state
    assert 'small_blind' in game_state
    assert 'big_blind' in game_state
    assert 'dealer_index' in game_state
    
    # Verify player info
    for player_info in game_state['players']:
        assert 'name' in player_info
        assert 'chips' in player_info
        assert 'bet' in player_info
        assert 'folded' in player_info
        assert 'position' in player_info
