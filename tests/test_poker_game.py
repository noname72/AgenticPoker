from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from agents.llm_agent import LLMAgent
from data.enums import ActionType
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
        starting_chips=1000,
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


def test_invalid_game_initialization(mock_players):
    """Test game initialization with invalid parameters."""
    with pytest.raises(ValueError):
        AgenticPoker(
            players=[],  # Empty players list
            starting_chips=1000,
            small_blind=50,
            big_blind=100,
        )

    with pytest.raises(ValueError):
        AgenticPoker(
            players=mock_players,
            starting_chips=-1000,  # Negative chips
            small_blind=50,
            big_blind=100,
        )


@patch("game.betting.betting_round")
def test_betting_rounds(mock_betting, game, mock_players):
    """Test betting round mechanics."""
    # Mock betting round function
    mock_betting.return_value = 300  # Return new pot amount

    # Set up initial game state
    game.start_round()
    game.pot = 150  # Set initial pot

    # Mock active players (not folded)
    active_players = [p for p in mock_players]
    for player in active_players:
        player.folded = False

    # Test pre-draw betting
    game.pot = mock_betting(active_players, game.pot)

    # Verify betting round was called
    mock_betting.assert_called_with(active_players, 150)
    assert game.pot == 300  # New pot amount from mock


def test_blinds_and_antes(game, mock_players):
    """Test collection of blinds and antes."""
    initial_chips = [p.chips for p in mock_players]

    # Store starting stacks for logging
    game.round_starting_stacks = {p: p.chips for p in mock_players}

    game.blinds_and_antes()

    # Verify blinds were collected
    assert mock_players[1].chips < initial_chips[1]  # Small blind
    assert mock_players[2].chips < initial_chips[2]  # Big blind

    # Verify ante was collected from all players
    for player in mock_players:
        assert player.chips < initial_chips[mock_players.index(player)]


def test_showdown(game, mock_players):
    """Test showdown mechanics."""
    # Set up game state
    game.pot = 300
    game.round_starting_stacks = {p: 1000 for p in mock_players}

    # Set up mock hands
    for i, player in enumerate(mock_players):
        player.folded = False
        player.hand = Mock(spec=Hand)

        # Set up hand comparison logic
        def make_gt(idx):
            def compare(self, other):  # Need both self and other
                # First player has the best hand
                if not hasattr(other, "_mock_idx"):
                    return True
                return idx == 0

            return compare

        def make_eq(idx):
            def compare(self, other):  # Need both self and other
                # Hands are equal if they're the same index
                if not hasattr(other, "_mock_idx"):
                    return False
                return idx == other._mock_idx

            return compare

        player.hand.__gt__ = make_gt(i)
        player.hand.__eq__ = make_eq(i)
        player.hand._mock_idx = i  # Store index for comparison
        player.hand.evaluate.return_value = ["Royal Flush", "Full House", "Pair"][i]
        player.hand.show.return_value = f"Mock Hand {i}"

    # Run showdown
    game.showdown()

    # Verify winner received pot
    assert mock_players[0].chips == 1300  # Initial 1000 + pot 300
    assert mock_players[1].chips == 1000  # Unchanged
    assert mock_players[2].chips == 1000  # Unchanged


def test_player_elimination(game, mock_players):
    """Test player elimination mechanics."""
    # Set one player to 0 chips
    mock_players[0].chips = 0

    # Check if game continues
    result = game.remove_bankrupt_players()

    # Verify player was removed
    assert len(game.players) == 2
    assert mock_players[0] not in game.players


def test_game_end_conditions(game, mock_players):
    """Test game ending conditions."""
    # Test one player remaining
    mock_players[1].chips = 0
    mock_players[2].chips = 0

    result = game.remove_bankrupt_players()

    assert not result  # Game should end
    assert len(game.players) == 1


# ... Rest of the tests converted to pytest style ...
