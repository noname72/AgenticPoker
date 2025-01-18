from unittest.mock import MagicMock, patch

import pytest

from data.states.round_state import RoundPhase
from data.types.action_response import ActionType
from data.types.pot_types import SidePot
from game.betting import (
    betting_round,
    collect_blinds_and_antes,
    handle_betting_round,
    validate_bet_to_call,
)


def test_validate_bet_to_call():
    """
    Tests the validate_bet_to_call function with various bet amounts.
    Verifies that:
    - When current bet is higher than player bet, returns the difference
    - When bets are equal, returns 0
    - When player bet is higher than current bet, returns 0
    """
    assert validate_bet_to_call(100, 50) == 50
    assert validate_bet_to_call(100, 100) == 0
    assert validate_bet_to_call(0, 0) == 0
    assert validate_bet_to_call(50, 100) == 0


def test_collect_blinds_and_antes(mock_game, mock_players, mock_betting_logger):
    """
    Tests collection of blinds and antes from players.
    Assumes:
    - 3+ players in mock_players
    - Players at indices 1 and 2 can post small and big blinds respectively
    - All players have sufficient chips for blinds and antes
    """
    mock_game.players = mock_players
    dealer_index = 0
    small_blind = 50
    big_blind = 100
    ante = 10

    collected = collect_blinds_and_antes(
        mock_players, dealer_index, small_blind, big_blind, ante, mock_game
    )

    assert collected == (ante * len(mock_players)) + small_blind + big_blind
    assert mock_players[1].bet == small_blind
    assert mock_players[2].bet == big_blind


@patch("game.betting.PlayerQueue")
def test_betting_round_no_all_in(mock_player_queue, mock_game, mock_player_with_action):
    """
    Tests a basic betting round where no players are all-in.
    Assumes:
    - Single player in the game
    - Player has sufficient chips and is not folded
    - Round completes after one player action
    """
    print("\n=== Starting test_betting_round_no_all_in ===")

    mock_game.players = [mock_player_with_action]
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.pot_manager.pot = 0
    mock_game.current_bet = 0

    # Set up mock player queue
    player_queue = mock_player_queue.return_value
    # Return False a few times then True to simulate round completion
    player_queue.is_round_complete.side_effect = [False, True]
    # Return our mock player once then None
    player_queue.get_next_player.side_effect = [mock_player_with_action, None]

    result = betting_round(mock_game)

    assert result == mock_game.pot_manager.pot
    mock_player_with_action.decide_action.assert_called_once_with(mock_game)
    mock_player_with_action.execute.assert_called_once()


def test_handle_betting_round_no_players(mock_game):
    """
    Tests that handle_betting_round raises ValueError when no players are in the game.
    """
    mock_game.players = []
    with pytest.raises(ValueError):
        handle_betting_round(mock_game)


def test_handle_betting_round_invalid_pot(mock_game, mock_player):
    """
    Tests that handle_betting_round raises ValueError when pot amount is negative.
    """
    mock_game.players = [mock_player]
    mock_game.pot_manager.pot = -100
    with pytest.raises(ValueError):
        handle_betting_round(mock_game)


def test_handle_betting_round_with_side_pots(
    mock_game, mock_player, mock_betting_round, mock_side_pot
):
    """
    Tests handling of a betting round that results in side pots.
    Assumes:
    - Single player in game
    - Betting round returns both main pot and side pots
    - Side pots are properly structured with amounts and eligible players
    """
    mock_game.players = [mock_player]
    side_pots = [mock_side_pot(50, [mock_player.name])]
    mock_betting_round.return_value = (150, side_pots)

    new_pot, returned_side_pots, should_continue = handle_betting_round(mock_game)

    assert new_pot == 150
    assert returned_side_pots == side_pots
    assert mock_game.pot_manager.pot == 150
    assert mock_game.pot_manager.side_pots == [
        {"amount": 50, "eligible_players": [mock_player.name]}
    ]
    assert should_continue is False


def test_handle_betting_round_without_side_pots(
    mock_game, mock_active_players, mock_betting_round
):
    """
    Tests handling of a normal betting round without side pots.
    Assumes:
    - Multiple active players
    - Initial pot of 100
    - Betting round increases pot to 150
    - No side pots are created
    """
    mock_game.players = mock_active_players
    mock_game.pot_manager.pot = 100
    mock_betting_round.return_value = 150

    new_pot, returned_side_pots, should_continue = handle_betting_round(mock_game)

    assert new_pot == 150
    assert returned_side_pots is None
    assert mock_game.pot_manager.pot == 150
    assert mock_game.pot_manager.side_pots is None
    assert should_continue is True


def test_should_skip_player_folded(mock_player):
    """
    Tests that _should_skip_player correctly identifies folded players.
    Verifies player should be skipped and returns appropriate reason.
    """
    mock_player.folded = True
    from game.betting import _should_skip_player

    should_skip, reason = _should_skip_player(mock_player, set())
    assert should_skip is True
    assert reason == "folded or has no chips"


def test_should_skip_player_no_chips(mock_player):
    """
    Tests that _should_skip_player correctly identifies players with no chips.
    Verifies player should be skipped and returns appropriate reason.
    """
    mock_player.chips = 0
    from game.betting import _should_skip_player

    should_skip, reason = _should_skip_player(mock_player, set())
    assert should_skip is True
    assert reason == "folded or has no chips"


def test_should_skip_player_not_needing_to_act(mock_player):
    from game.betting import _should_skip_player

    should_skip, reason = _should_skip_player(mock_player, set())
    assert should_skip is True
    assert reason == "doesn't need to act"


def test_should_not_skip_player(mock_player):
    from game.betting import _should_skip_player

    should_skip, reason = _should_skip_player(mock_player, {mock_player})
    assert should_skip is False
    assert reason == ""


def test_collect_blinds_and_antes_no_ante(mock_game, mock_players, mock_betting_logger):
    mock_game.players = mock_players
    dealer_index = 0
    small_blind = 50
    big_blind = 100
    ante = 0

    collected = collect_blinds_and_antes(
        mock_players, dealer_index, small_blind, big_blind, ante, mock_game
    )

    assert collected == small_blind + big_blind
    assert mock_players[1].place_bet.called
    assert mock_players[2].place_bet.called
    mock_betting_logger.log_collecting_antes.assert_not_called()


def test_get_big_blind_player(mock_game, mock_big_blind_player):
    from game.betting import _get_big_blind_player

    active_players = [mock_big_blind_player]
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.round_state.big_blind_position = 0

    big_blind_player = _get_big_blind_player(mock_game, active_players)
    assert big_blind_player == mock_big_blind_player
    assert mock_big_blind_player.is_big_blind is True


@patch("game.betting.PlayerQueue")
def test_betting_round_with_all_in(
    mock_player_queue_class,
    mock_game,
    mock_all_in_player,
    mock_pot_with_side_pots,
):
    """
    Tests a complex betting round involving an all-in player.
    Assumes:
    - Two players: one all-in and one active
    - All-in player bet is 1000
    - Active player bet is 1500
    - Should create two side pots:
        1. Main pot of 2000 (both players eligible)
        2. Side pot of 500 (only active player eligible)
    """
    print("\n=== Starting test_betting_round_with_all_in ===")
    # Set up players
    mock_active_player = MagicMock(name="ActivePlayer")
    mock_active_player.name = "Player1"
    mock_active_player.folded = False
    mock_active_player.is_all_in = False
    mock_active_player.bet = 1500
    mock_active_player.chips = 500

    mock_all_in_player.name = "AllInPlayer"
    mock_all_in_player.is_all_in = True
    mock_all_in_player.bet = 1000
    mock_all_in_player.chips = 0
    mock_all_in_player.folded = False

    # Set up game state
    mock_game.players = [mock_all_in_player, mock_active_player]
    mock_game.pot_manager = mock_pot_with_side_pots
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.current_bet = 1500  # Match the active player's bet

    # Configure player queue
    player_queue = MagicMock()
    mock_player_queue_class.return_value = player_queue
    player_queue.is_round_complete.side_effect = [False, False, True]
    player_queue.get_next_player.side_effect = [
        mock_all_in_player,
        mock_active_player,
        None,
    ]
    player_queue.players = [mock_all_in_player, mock_active_player]

    # Configure pot manager
    mock_pot_with_side_pots.pot = 0
    side_pots = [
        SidePot(
            amount=2000,  # 1000 (all-in amount) * 2 players
            eligible_players=["AllInPlayer", "Player1"],
        ),
        SidePot(amount=500, eligible_players=["Player1"]),  # (1500 - 1000) * 1 player
    ]
    # Configure both the return value and the actual side pots
    mock_pot_with_side_pots.calculate_side_pots.return_value = side_pots
    mock_pot_with_side_pots.side_pots = side_pots.copy()

    # Configure action responses
    action_response = MagicMock()
    action_response.action_type = ActionType.CALL
    mock_all_in_player.decide_action.return_value = action_response
    mock_active_player.decide_action.return_value = action_response

    result = betting_round(mock_game)

    print(f"\nAfter betting round:")
    print(f"- Result type: {type(result)}")
    if isinstance(result, tuple):
        print(f"- Result[0] (pot): {result[0]}")
        print(f"- Result[1] (side pots): {result[1]}")
    print(f"- decide_action called: {mock_all_in_player.decide_action.called}")
    print(f"- decide_action call count: {mock_all_in_player.decide_action.call_count}")

    assert isinstance(result, tuple)
    assert len(result[1]) == 2  # Two side pots
    assert result[1][0].amount == 2000  # First side pot amount (both players)
    assert result[1][1].amount == 500  # Second side pot amount (only active player)
    assert "AllInPlayer" in result[1][0].eligible_players  # All-in player in first pot
    assert "Player1" in result[1][0].eligible_players  # Active player in first pot
    assert (
        "AllInPlayer" not in result[1][1].eligible_players
    )  # All-in player not in second pot
    assert "Player1" in result[1][1].eligible_players  # Active player in second pot


@patch("game.betting.PlayerQueue")
def test_betting_round_multiple_players(
    mock_player_queue_class, mock_game, mock_active_players, mock_action_response
):
    """
    Tests a betting round with multiple active players.
    Assumes:
    - Two active players
    - Flop betting round
    - Each player acts once before round completes
    - All players have sufficient chips and make valid actions
    """
    mock_game.players = mock_active_players[:2]  # Use first two players
    mock_game.round_state.phase = RoundPhase.FLOP

    # Configure the mock player queue
    player_queue = mock_player_queue_class.return_value
    player_queue.is_round_complete.side_effect = [False, False, True]
    player_queue.get_next_player.side_effect = [
        mock_active_players[0],
        mock_active_players[1],
        None,
    ]
    player_queue.players = mock_game.players

    # Set up action responses
    for player in mock_game.players:
        player.decide_action.return_value = mock_action_response
        player.execute = MagicMock()

    result = betting_round(mock_game)

    assert result == mock_game.pot_manager.pot
    for player in mock_game.players:
        player.decide_action.assert_called_once()


def test_update_action_tracking_raise(mock_betting_state):
    """
    Tests action tracking updates after a raise.
    Verifies:
    - Raiser becomes last raiser
    - Raiser is added to acted_since_last_raise
    - Raiser is removed from needs_to_act
    - All other players are added to needs_to_act
    Assumes all players have sufficient chips and are not folded.
    """
    from game.betting import _update_action_tracking

    state = mock_betting_state
    player = state["active_players"][0]
    player.folded = False
    player.chips = 1000

    # Configure other players
    for p in state["active_players"][1:]:
        p.folded = False
        p.chips = 1000

    last_raiser, needs_to_act, acted_since_last_raise = _update_action_tracking(
        player,
        ActionType.RAISE,
        state["active_players"],
        state["needs_to_act"],
        state["acted_since_last_raise"],
        None,  # big_blind_player
        False,  # is_preflop
    )

    assert last_raiser == player
    assert player in acted_since_last_raise
    assert player not in needs_to_act
    # Verify other players need to act after a raise
    for p in state["active_players"][1:]:
        assert p in needs_to_act


def test_update_action_tracking_call(mock_betting_state):
    """
    Tests action tracking updates after a call.
    Verifies:
    - Last raiser remains unchanged
    - Caller is added to acted_since_last_raise
    - Caller is removed from needs_to_act
    Assumes all players have sufficient chips and are not folded.
    """
    from game.betting import _update_action_tracking

    state = mock_betting_state
    player = state["active_players"][0]
    player.folded = False
    player.chips = 1000

    # Configure other players
    for p in state["active_players"][1:]:
        p.folded = False
        p.chips = 1000

    last_raiser, needs_to_act, acted_since_last_raise = _update_action_tracking(
        player,
        ActionType.CALL,
        state["active_players"],
        state["needs_to_act"],
        state["acted_since_last_raise"],
        None,  # big_blind_player
        False,  # is_preflop
    )

    assert last_raiser is None
    assert player in acted_since_last_raise
    assert player not in needs_to_act
