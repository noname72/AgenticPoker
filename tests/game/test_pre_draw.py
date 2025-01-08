from data.types.base_types import DeckState
from data.types.game_state import GameState
from data.types.pot_types import PotState
from data.types.round_state import RoundState

import pytest

from game.player import Player
from game.pre_draw import handle_pre_draw_betting


@pytest.fixture
def basic_game_state():
    """Create a basic GameState for testing."""
    return GameState(
        players=[],  # Will be populated in tests
        dealer_position=0,
        small_blind=10,
        big_blind=20,
        ante=0,
        min_bet=20,
        round_state=RoundState(
            round_number=1, phase="pre_draw", current_bet=20, raise_count=0
        ),
        pot_state=PotState(main_pot=0),
        deck_state=DeckState(cards_remaining=52),
    )


def test_handle_pre_draw_betting_simple_case(basic_game_state):
    """Test a simple pre-draw betting case where all players call."""
    players = [
        Player("Player 1", 1000),
        Player("Player 2", 1000),
        Player("Player 3", 1000),
    ]

    # Mock player decisions
    for player in players:
        player.decide_action = lambda x: ("call", 20)

    new_pot, side_pots, should_continue = handle_pre_draw_betting(
        players=players, pot=0, dealer_index=0, game_state=basic_game_state
    )

    assert new_pot == 60  # Each player bet 20
    assert side_pots is None
    assert should_continue is True
    assert all(p.bet == 20 for p in players)
    assert all(p.chips == 980 for p in players)


def test_handle_pre_draw_betting_with_raises(basic_game_state):
    """Test pre-draw betting with raises."""
    players = [
        Player("Player 1", 1000),
        Player("Player 2", 1000),
        Player("Player 3", 1000),
    ]

    # Setup betting sequence
    players[0].decide_action = lambda x: ("raise", 40)
    players[1].decide_action = lambda x: ("raise", 80)
    players[2].decide_action = lambda x: ("call", 80)

    new_pot, side_pots, should_continue = handle_pre_draw_betting(
        players=players, pot=0, dealer_index=0, game_state=basic_game_state
    )

    assert new_pot == 240  # 80 × 3
    assert side_pots is None
    assert should_continue is True


def test_handle_pre_draw_betting_all_fold(basic_game_state):
    """Test when all players except one fold."""
    players = [
        Player("Player 1", 1000),
        Player("Player 2", 1000),
        Player("Player 3", 1000),
    ]

    # Setup folding sequence
    players[0].decide_action = lambda x: ("raise", 40)
    players[1].decide_action = lambda x: ("fold", 0)
    players[2].decide_action = lambda x: ("fold", 0)

    new_pot, side_pots, should_continue = handle_pre_draw_betting(
        players=players, pot=0, dealer_index=0, game_state=basic_game_state
    )

    assert new_pot == 40
    assert side_pots is None
    assert should_continue is False  # Game should end when all but one fold
    assert not players[0].folded
    assert players[1].folded
    assert players[2].folded


def test_handle_pre_draw_betting_all_in(basic_game_state):
    """Test all-in scenarios during pre-draw betting."""
    players = [
        Player("Player 1", 100),
        Player("Player 2", 50),
        Player("Player 3", 150),
    ]

    # Setup betting sequence leading to all-in
    players[0].decide_action = lambda x: ("raise", 100)  # All-in
    players[1].decide_action = lambda x: ("call", 100)  # Partial call (all-in)
    players[2].decide_action = lambda x: ("call", 100)

    new_pot, side_pots, should_continue = handle_pre_draw_betting(
        players=players, pot=0, dealer_index=0, game_state=basic_game_state
    )

    assert new_pot == 250  # 100 + 50 + 100
    assert len(side_pots) == 2
    assert should_continue is True


def test_handle_pre_draw_betting_invalid_actions(basic_game_state):
    """Test handling of invalid betting actions."""
    players = [
        Player("Player 1", 1000),
        Player("Player 2", 1000),
        Player("Player 3", 1000),
    ]

    # Setup invalid actions that should be converted to calls
    players[0].decide_action = lambda x: ("invalid_action", 20)
    players[1].decide_action = lambda x: ("raise", 15)  # Below minimum
    players[2].decide_action = lambda x: ("call", 20)

    new_pot, side_pots, should_continue = handle_pre_draw_betting(
        players=players, pot=0, dealer_index=0, game_state=basic_game_state
    )

    assert new_pot == 60  # All should be converted to calls (20 × 3)
    assert side_pots is None
    assert should_continue is True
    assert all(p.bet == 20 for p in players)
