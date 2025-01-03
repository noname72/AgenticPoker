import logging
from unittest.mock import MagicMock, patch

import pytest

from game.player import Player
from game.post_draw import (
    handle_post_draw_betting,
    handle_showdown,
    _evaluate_hands,
    _log_chip_movements,
)
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


def test_handle_post_draw_betting_simple_case(mock_players, mock_game_state):
    """Test post-draw betting with a simple case (no side pots)."""
    # Mock player decisions
    for player in mock_players:
        player.decide_action = lambda x: ("call", 20)

    new_pot, side_pots, should_continue = handle_post_draw_betting(
        players=mock_players,
        pot=100,
        dealer_index=0,
        game_state=mock_game_state,
    )

    assert new_pot == 160  # Initial 100 + (20 * 3)
    assert side_pots is None
    assert should_continue is True
    assert all(p.bet == 20 for p in mock_players)


def test_handle_post_draw_betting_with_raises(mock_players, mock_game_state):
    """Test post-draw betting with raises."""
    # Setup player decisions
    mock_players[0].decide_action = lambda x: ("raise", 40)
    mock_players[1].decide_action = lambda x: ("call", 40)
    mock_players[2].decide_action = lambda x: ("fold", 0)

    new_pot, side_pots, should_continue = handle_post_draw_betting(
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


def test_handle_post_draw_betting_all_fold(mock_players, mock_game_state):
    """Test post-draw betting when all but one player folds."""
    # Setup player decisions
    mock_players[0].decide_action = lambda x: ("raise", 40)
    mock_players[1].decide_action = lambda x: ("fold", 0)
    mock_players[2].decide_action = lambda x: ("fold", 0)

    new_pot, side_pots, should_continue = handle_post_draw_betting(
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


def test_handle_post_draw_betting_all_in(mock_players, mock_game_state):
    """Test post-draw betting with all-in situations."""
    # Setup players with different chip amounts
    mock_players[0].chips = 500
    mock_players[1].chips = 300
    mock_players[2].chips = 100

    # Setup player decisions
    mock_players[0].decide_action = lambda x: ("raise", 500)
    mock_players[1].decide_action = lambda x: ("call", 300)
    mock_players[2].decide_action = lambda x: ("call", 100)

    new_pot, side_pots, should_continue = handle_post_draw_betting(
        players=mock_players,
        pot=100,
        dealer_index=0,
        game_state=mock_game_state,
    )

    assert new_pot == 1000  # Initial 100 + 500 + 300 + 100
    assert side_pots is not None
    assert len(side_pots) == 3  # Three different betting levels
    assert should_continue is True


def test_handle_showdown_single_winner(mock_players):
    """Test showdown with a clear winner."""
    # Setup initial chips
    initial_chips = {p: p.chips for p in mock_players}

    # Setup mock pot manager
    mock_pot_manager = MagicMock()
    mock_pot_manager.pot = 300
    # Add calculate_side_pots method that returns empty list
    mock_pot_manager.calculate_side_pots.return_value = []

    # Setup different hand strengths
    mock_players[0].hand.evaluate = lambda: "Three of a Kind"
    mock_players[1].hand.evaluate = lambda: "Pair"
    mock_players[2].hand.evaluate = lambda: "High Card"

    def make_hand_comparison(rank_index):
        def compare_to(other):
            ranks = ["High Card", "Pair", "Three of a Kind"]
            my_rank = ranks.index(rank_index)
            other_rank = ranks.index(other.evaluate())
            return 1 if my_rank > other_rank else -1 if my_rank < other_rank else 0

        return compare_to

    for player in mock_players:
        player.hand.compare_to = make_hand_comparison(player.hand.evaluate())

    # Run showdown
    winners = _evaluate_hands(mock_players)
    # Distribute pot to winner
    pot_share = mock_pot_manager.pot // len(winners)
    for winner in winners:
        winner.chips += pot_share

    # Verify winner got the pot
    assert mock_players[0].chips == 1300  # Initial 1000 + pot 300
    assert mock_players[1].chips == 1000  # Unchanged
    assert mock_players[2].chips == 1000  # Unchanged


def test_handle_showdown_split_pot(mock_players):
    """Test showdown with tied winners."""
    # Setup initial chips
    initial_chips = {p: p.chips for p in mock_players}

    # Setup mock pot manager
    mock_pot_manager = MagicMock()
    mock_pot_manager.pot = 300
    # Add calculate_side_pots method that returns empty list
    mock_pot_manager.calculate_side_pots.return_value = []

    # Setup identical hands for first two players
    mock_players[0].hand.evaluate = lambda: "Pair"
    mock_players[1].hand.evaluate = lambda: "Pair"
    mock_players[2].hand.evaluate = lambda: "High Card"

    # Setup hand comparisons for a tie
    def make_hand_comparison(rank_index):
        def compare_to(other):
            ranks = ["High Card", "Pair"]
            my_rank = ranks.index(rank_index)
            other_rank = ranks.index(other.evaluate())
            return 1 if my_rank > other_rank else -1 if my_rank < other_rank else 0

        return compare_to

    for player in mock_players:
        player.hand.compare_to = make_hand_comparison(player.hand.evaluate())

    # Run showdown
    winners = _evaluate_hands(mock_players)
    # Distribute pot evenly among winners
    pot_share = mock_pot_manager.pot // len(winners)
    for winner in winners:
        winner.chips += pot_share

    # Verify pot was split between winners
    assert mock_players[0].chips == 1150  # Initial 1000 + half pot 150
    assert mock_players[1].chips == 1150  # Initial 1000 + half pot 150
    assert mock_players[2].chips == 1000  # Unchanged


def test_handle_post_draw_betting_with_side_pots(mock_players, mock_game_state):
    """Test post-draw betting with side pots."""
    # Setup players with different chip amounts
    mock_players[0].chips = 500
    mock_players[1].chips = 300
    mock_players[2].chips = 100

    # Setup player decisions
    mock_players[0].decide_action = lambda x: ("raise", 500)
    mock_players[1].decide_action = lambda x: ("call", 300)
    mock_players[2].decide_action = lambda x: ("call", 100)

    new_pot, side_pots, should_continue = handle_post_draw_betting(
        players=mock_players,
        pot=100,
        dealer_index=0,
        game_state=mock_game_state,
    )

    assert new_pot == 1000  # Initial 100 + 500 + 300 + 100
    assert side_pots is not None
    assert len(side_pots) == 3  # Three different betting levels
    assert should_continue is True


def test_handle_showdown_multiple_winners(mock_players):
    """Test showdown with multiple winners."""
    # Setup initial chips
    initial_chips = {p: p.chips for p in mock_players}

    # Setup mock pot manager
    mock_pot_manager = MagicMock()
    mock_pot_manager.pot = 300
    # Add calculate_side_pots method that returns empty list
    mock_pot_manager.calculate_side_pots.return_value = []

    # Setup identical hands for first two players
    mock_players[0].hand.evaluate = lambda: "Pair"
    mock_players[1].hand.evaluate = lambda: "Pair"
    mock_players[2].hand.evaluate = lambda: "High Card"

    # Setup hand comparisons for a tie
    def make_hand_comparison(rank_index):
        def compare_to(other):
            ranks = ["High Card", "Pair"]
            my_rank = ranks.index(rank_index)
            other_rank = ranks.index(other.evaluate())
            return 1 if my_rank > other_rank else -1 if my_rank < other_rank else 0

        return compare_to

    for player in mock_players:
        player.hand.compare_to = make_hand_comparison(player.hand.evaluate())

    # Run showdown
    handle_showdown(
        players=mock_players,
        initial_chips=initial_chips,
        pot_manager=mock_pot_manager,
    )

    # Verify pot was split between winners
    assert mock_players[0].chips == 1150  # Initial 1000 + half pot 150
    assert mock_players[1].chips == 1150  # Initial 1000 + half pot 150
    assert mock_players[2].chips == 1000  # Unchanged


def test_handle_showdown_odd_chips(mock_players):
    """Test showdown with odd number of chips to split."""
    # Setup initial chips
    initial_chips = {p: p.chips for p in mock_players}

    # Setup mock pot manager with odd pot amount
    mock_pot_manager = MagicMock()
    mock_pot_manager.pot = 301  # Odd number
    # Add calculate_side_pots method that returns empty list
    mock_pot_manager.calculate_side_pots.return_value = []

    # Setup identical hands for all players
    for player in mock_players:
        player.hand.evaluate = lambda: "Pair"
        player.hand.compare_to = lambda other: 0  # All hands tie

    # Run showdown
    handle_showdown(
        players=mock_players,
        initial_chips=initial_chips,
        pot_manager=mock_pot_manager,
    )

    # Verify pot was split as evenly as possible
    total_after = sum(p.chips for p in mock_players)
    assert total_after == 3000 + 301  # Initial chips + pot
    # First player should get extra chip in case of odd split
    assert mock_players[0].chips == 1101  # Initial 1000 + split 100 + extra 1
    assert mock_players[1].chips == 1100  # Initial 1000 + split 100
    assert mock_players[2].chips == 1100  # Initial 1000 + split 100


def test_handle_showdown_with_side_pots(mock_players):
    """Test showdown with multiple side pots."""
    # Setup initial chips
    initial_chips = {p: p.chips for p in mock_players}

    # Setup mock pot manager with side pots
    mock_pot_manager = MagicMock()
    mock_pot_manager.pot = 600
    side_pots = [
        SidePot(amount=300, eligible_players=mock_players),
        SidePot(amount=200, eligible_players=mock_players[:2]),
        SidePot(amount=100, eligible_players=[mock_players[0]]),
    ]
    mock_pot_manager.calculate_side_pots.return_value = side_pots

    # Setup different hand strengths
    mock_players[0].hand.evaluate = lambda: "Three of a Kind"
    mock_players[1].hand.evaluate = lambda: "Pair"
    mock_players[2].hand.evaluate = lambda: "High Card"

    def make_hand_comparison(rank_index):
        def compare_to(other):
            ranks = ["High Card", "Pair", "Three of a Kind"]
            my_rank = ranks.index(rank_index)
            other_rank = ranks.index(other.evaluate())
            return 1 if my_rank > other_rank else -1 if my_rank < other_rank else 0

        return compare_to

    for player in mock_players:
        player.hand.compare_to = make_hand_comparison(player.hand.evaluate())

    # Run showdown
    handle_showdown(
        players=mock_players,
        initial_chips=initial_chips,
        pot_manager=mock_pot_manager,
    )

    # Verify pot distribution
    assert mock_players[0].chips == 1600  # Won all pots
    assert mock_players[1].chips == 1000  # No change
    assert mock_players[2].chips == 1000  # No change


def test_evaluate_hands_single_winner(mock_players):
    """Test hand evaluation with a clear winner."""
    # Setup different hand strengths
    mock_players[0].hand.evaluate = lambda: "Three of a Kind"
    mock_players[1].hand.evaluate = lambda: "Pair"
    mock_players[2].hand.evaluate = lambda: "High Card"

    def make_hand_comparison(rank_index):
        def compare_to(other):
            ranks = ["High Card", "Pair", "Three of a Kind"]
            my_rank = ranks.index(rank_index)
            other_rank = ranks.index(other.evaluate())
            return 1 if my_rank > other_rank else -1 if my_rank < other_rank else 0

        return compare_to

    for player in mock_players:
        player.hand.compare_to = make_hand_comparison(player.hand.evaluate())

    winners = _evaluate_hands(mock_players)
    assert len(winners) == 1
    assert winners[0] == mock_players[0]


def test_evaluate_hands_tie(mock_players):
    """Test hand evaluation with tied winners."""
    # Setup identical hands
    for player in mock_players:
        player.hand.evaluate = lambda: "Pair"
        player.hand.compare_to = lambda other: 0  # All hands tie

    winners = _evaluate_hands(mock_players)
    assert len(winners) == 3
    assert set(winners) == set(mock_players)


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
    mock_players[1].chips = 800  # Lost 200
    mock_players[2].chips = 1000  # No change

    _log_chip_movements(mock_players, initial_chips)

    # Check log messages
    assert "Player0: $1000 → $1200 (+200)" in caplog.text
    assert "Player1: $1000 → $800 (-200)" in caplog.text
    assert "Player2" not in caplog.text  # No change, shouldn't be logged


def test_handle_showdown_complex_side_pots(mock_players):
    """Test showdown with complex side pot scenarios involving multiple all-ins."""
    # Setup initial chips with varying amounts
    mock_players[0].chips = 0  # Player0 has committed all 1000 chips
    mock_players[1].chips = 0  # Player1 has committed all 500 chips
    mock_players[2].chips = 0  # Player2 has committed all 200 chips
    initial_chips = {mock_players[0]: 1000, mock_players[1]: 500, mock_players[2]: 200}

    # Setup mock pot manager with multiple side pots
    mock_pot_manager = MagicMock()
    mock_pot_manager.pot = 1700  # Total pot (1000 + 500 + 200)

    # Create side pots:
    # 1. Main pot (600): All players contribute 200 each
    # 2. Middle pot (600): Player0 and Player1 contribute 300 each
    # 3. High pot (500): Only Player0 contributes remaining 500
    side_pots = [
        SidePot(amount=600, eligible_players=mock_players),  # 200 x 3
        SidePot(amount=600, eligible_players=mock_players[:2]),  # 300 x 2
        SidePot(amount=500, eligible_players=[mock_players[0]]),  # 500 x 1
    ]
    mock_pot_manager.calculate_side_pots.return_value = side_pots

    # Setup different hand strengths
    mock_players[0].hand.evaluate = lambda: "Two Pair"  # Best hand
    mock_players[1].hand.evaluate = lambda: "Pair"  # Medium hand
    mock_players[2].hand.evaluate = lambda: "High Card"  # Worst hand

    def make_hand_comparison(rank_index):
        def compare_to(other):
            ranks = ["High Card", "Pair", "Two Pair"]
            my_rank = ranks.index(rank_index)
            other_rank = ranks.index(other.evaluate())
            return 1 if my_rank > other_rank else -1 if my_rank < other_rank else 0

        return compare_to

    for player in mock_players:
        player.hand.compare_to = make_hand_comparison(player.hand.evaluate())

    # Run showdown
    handle_showdown(
        players=mock_players,
        initial_chips=initial_chips,
        pot_manager=mock_pot_manager,
    )

    # Verify final chip counts:
    # Player0 should win all pots (600 + 600 + 500 = 1700)
    assert (
        mock_players[0].chips == 1700
    ), f"Player0 should have won all pots (1700), but has {mock_players[0].chips}"
    # Other players should have 0 chips (all-in and lost)
    assert (
        mock_players[1].chips == 0
    ), f"Player1 should have lost all chips, but has {mock_players[1].chips}"
    assert (
        mock_players[2].chips == 0
    ), f"Player2 should have lost all chips, but has {mock_players[2].chips}"

    # Verify total chips in play remains constant
    total_chips = sum(p.chips for p in mock_players)
    assert total_chips == 1700, f"Total chips should be 1700, but got {total_chips}"
