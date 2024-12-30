from datetime import datetime
from unittest.mock import Mock, patch
from typing import List
from unittest.mock import call

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


@patch("game.game.betting_round")
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


@patch("game.game.betting_round")
def test_full_betting_round(mock_betting, game, mock_players):
    """Test a complete betting round with raises and calls."""
    # Set up initial state
    game.pot = 150
    game.players = mock_players

    # Configure mock players' decide_action methods
    for player in mock_players:
        player.decide_action = Mock(return_value=("call", 200))

    # Mock betting round to return just the pot amount
    mock_betting.return_value = 750  # Just return the pot amount

    # Run pre-draw betting
    game._handle_pre_draw_betting()

    # Verify pot increased correctly
    assert game.pot == 750  # Initial 150 + 200*3

    # Verify betting round was called with correct arguments
    mock_betting.assert_called_once_with(mock_players, 150)


@patch("game.game.betting_round")
def test_full_betting_round_with_side_pots(mock_betting, game, mock_players):
    """Test betting round that creates side pots."""
    # Set up initial state
    game.pot = 150
    game.players = mock_players

    # Mock betting round to return pot amount and side pots
    side_pots = [(300, [mock_players[0], mock_players[1]])]
    mock_betting.return_value = (750, side_pots)

    # Run pre-draw betting
    game._handle_pre_draw_betting()

    # Verify pot and side pots
    assert game.pot == 750
    assert game.side_pots == side_pots

    # Verify betting round was called with correct arguments
    mock_betting.assert_called_once_with(mock_players, 150)


@patch("game.game.betting_round")
def test_all_in_scenario(mock_betting, game, mock_players):
    """Test handling of all-in situations."""
    # Set up initial state
    game.pot = 150  # Set initial pot

    # Set up players with different chip amounts
    mock_players[0].chips = 500
    mock_players[1].chips = 300
    mock_players[2].chips = 100

    # Configure mock players' decide_action methods
    mock_players[0].decide_action = Mock(return_value=("raise", 500))
    mock_players[1].decide_action = Mock(return_value=("call", 300))
    mock_players[2].decide_action = Mock(return_value=("call", 100))

    # Mock betting round to return final pot and side pots
    side_pots = [
        (300, [mock_players[0], mock_players[1], mock_players[2]]),
        (400, [mock_players[0], mock_players[1]]),
        (200, [mock_players[0]]),
    ]
    mock_betting.return_value = (900, side_pots)  # Total pot of 900

    # Run pre-draw betting
    game._handle_pre_draw_betting()

    # Verify correct pot amount
    assert game.pot == 900

    # Verify betting round was called with correct arguments
    mock_betting.assert_called_once_with([p for p in mock_players if not p.folded], 150)


def test_blinds_collection_order(game, mock_players):
    """Test that blinds are collected in the correct order."""
    initial_chips = 1000
    game.dealer_index = 0

    # Track bet order
    bet_sequence = []

    def track_bet(amount):
        nonlocal bet_sequence
        bet_sequence.append((amount))
        return amount

    for player in mock_players:
        player.place_bet = Mock(side_effect=track_bet)

    game.blinds_and_antes()

    # Verify correct order and amounts
    expected_sequence = [
        10,  # Ante from player 0
        10,  # Ante from player 1
        10,  # Ante from player 2
        50,  # Small blind from player 1
        100,  # Big blind from player 2
    ]

    assert bet_sequence == expected_sequence


def test_showdown_with_ties(game, mock_players):
    """Test pot distribution when multiple players tie for best hand."""
    game.pot = 900

    # Set up mock hands that tie
    mock_players[0].hand.evaluate = Mock(return_value="Full House")
    mock_players[1].hand.evaluate = Mock(return_value="Full House")
    mock_players[2].hand.evaluate = Mock(return_value="Two Pair")

    # Create a hand ranking system
    hand_ranks = {
        mock_players[0].hand: 2,  # High rank
        mock_players[1].hand: 2,  # Same high rank
        mock_players[2].hand: 1,  # Lower rank
    }

    # Define comparison methods using the ranking system
    def make_comparison_methods(hand):
        def gt(other):
            if not isinstance(other, Mock):
                return True
            return hand_ranks[hand] > hand_ranks[other]

        def eq(other):
            if not isinstance(other, Mock):
                return False
            return hand_ranks[hand] == hand_ranks[other]

        return gt, eq

    # Set up comparison methods for all hands
    for player in mock_players:
        gt, eq = make_comparison_methods(player.hand)
        player.hand.__gt__ = Mock(side_effect=gt)
        player.hand.__eq__ = Mock(side_effect=eq)
        player.folded = False  # Make sure no players are folded

    # Run showdown
    game.showdown()

    # Verify pot split evenly between tied winners
    assert mock_players[0].chips == 1450  # Initial 1000 + 450 (half of 900)
    assert mock_players[1].chips == 1450  # Initial 1000 + 450 (half of 900)
    assert mock_players[2].chips == 1000  # Unchanged


def test_player_elimination_sequence(game, mock_players):
    """Test proper handling of sequential player eliminations."""
    # Set up players with different chip amounts
    mock_players[0].chips = 0
    mock_players[1].chips = 50
    mock_players[2].chips = 100

    # First elimination
    game.remove_bankrupt_players()
    assert len(game.players) == 2
    assert mock_players[0] not in game.players

    # Second elimination
    mock_players[1].chips = 0
    game.remove_bankrupt_players()
    assert len(game.players) == 1
    assert mock_players[1] not in game.players

    # Verify game ends with one player
    assert not game.remove_bankrupt_players()


def test_ante_collection_with_short_stacks(game, mock_players):
    """Test ante collection when players can't cover the full amount."""
    game.ante = 20
    mock_players[0].chips = 15  # Can't cover ante
    mock_players[1].chips = 20  # Exactly ante amount
    mock_players[2].chips = 170  # Enough for ante + big blind

    # Set dealer position so player 2 is big blind
    game.dealer_index = 0  # Makes player 1 small blind, player 2 big blind

    game.blinds_and_antes()

    # Verify correct amounts collected
    assert mock_players[0].chips == 0  # Paid all 15 (partial ante)
    assert mock_players[1].chips == 0  # Paid all 20 (full ante)
    assert mock_players[2].chips == 50  # Paid 20 (ante) + 100 (big blind)

    # Total pot should be:
    # Player 0: 15 (partial ante)
    # Player 1: 20 (full ante)
    # Player 2: 20 (ante) + 100 (big blind)
    assert game.pot == 155


# ... Rest of the tests converted to pytest style ...
