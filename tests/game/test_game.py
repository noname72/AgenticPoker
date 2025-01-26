from datetime import datetime
from unittest.mock import Mock

import pytest

from agents.agent import Agent
from game import AgenticPoker
from game.card import Card
from game.draw import handle_draw_phase
from game.hand import Hand


@pytest.fixture
def mock_players():
    """Fixture to create mock players."""
    players = []
    for name in ["Alice", "Bob", "Charlie"]:
        player = Mock(spec=Agent)
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
    assert len(game.table) == 3
    assert game.small_blind == 50
    assert game.big_blind == 100
    assert game.ante == 10
    assert game.session_id is not None
    # Verify all players have initial chips
    for player in game.table:
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
            Mock(spec=Agent, chips=-1000, name=f"Player{i}") for i in range(3)
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

    # Reset round which rotates dealer
    game._reset_round()

    # Verify dealer rotated
    expected_dealer = (initial_dealer + 1) % len(mock_players)
    assert game.dealer_index == expected_dealer


def test_round_initialization(game, mock_players):
    """Test initialization of a new round."""
    game._initialize_round()

    # Verify round state
    assert game.pot.pot == 0
    assert all(player.bet == 0 for player in game.table)
    assert all(not player.folded for player in game.table)
    assert all(hasattr(player, "hand") for player in game.table)


def test_collect_blinds_and_antes(game, player_factory):
    """Test that blinds and antes are collected correctly and pot is updated properly."""
    # Create players with known chip stacks
    players = [
        player_factory(name="Alice", chips=1000),
        player_factory(name="Bob", chips=1000),
        player_factory(name="Charlie", chips=1000),
    ]
    game.table.players = players

    # Set up initial state
    game.small_blind = 50
    game.big_blind = 100
    game.ante = 10
    game.dealer_index = 0

    # Store initial chip counts
    initial_chips = {p: p.chips for p in game.table}

    # Collect blinds and antes
    game._collect_blinds_and_antes()

    # Calculate expected pot amount
    num_players = len(players)
    expected_antes = num_players * game.ante  # 3 players * $10 = $30
    expected_blinds = game.small_blind + game.big_blind  # $50 + $100 = $150
    expected_pot = expected_antes + expected_blinds  # $30 + $150 = $180

    # Verify pot amount
    assert (
        game.pot.pot == expected_pot
    ), f"Expected pot of ${expected_pot}, got ${game.pot.pot}"

    # Verify player chip counts
    dealer = game.table[0]  # Alice
    sb_player = game.table[1]  # Bob
    bb_player = game.table[2]  # Charlie

    # Check dealer's chips (only pays ante)
    assert dealer.chips == initial_chips[dealer] - game.ante

    # Check small blind player's chips (pays ante + small blind)
    assert sb_player.chips == initial_chips[sb_player] - game.ante - game.small_blind

    # Check big blind player's chips (pays ante + big blind)
    assert bb_player.chips == initial_chips[bb_player] - game.ante - game.big_blind

    # Verify current bet is set to big blind
    assert game.current_bet == game.big_blind
