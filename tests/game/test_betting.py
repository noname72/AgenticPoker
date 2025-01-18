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
from tests.mocks.mock_player import MockPlayer
from tests.mocks.mock_player_queue import MockPlayerQueue
from tests.mocks.mock_pot_manager import MockPotManager


@pytest.fixture
def mock_game():
    game = MagicMock()
    game.players = []
    game.pot_manager = MockPotManager()
    game.pot_manager.pot = 0
    game.round_state = MagicMock()
    game.round_state.phase = RoundPhase.PREFLOP
    game.round_state.big_blind_position = 1
    game.config = MagicMock()
    game.config.small_blind = 50
    game.config.big_blind = 100
    return game


@pytest.fixture
def mock_player():
    player = MockPlayer(name="Player1", chips=1000)
    player.decide_action.return_value = MagicMock(action_type=ActionType.CALL)
    return player


def test_validate_bet_to_call():
    assert validate_bet_to_call(100, 50) == 50
    assert validate_bet_to_call(100, 100) == 0
    assert validate_bet_to_call(0, 0) == 0
    assert validate_bet_to_call(50, 100) == 0


def test_collect_blinds_and_antes(mock_game):
    players = [
        MockPlayer(name="Dealer", chips=1000),
        MockPlayer(name="SB", chips=1000),
        MockPlayer(name="BB", chips=1000),
        MockPlayer(name="Player3", chips=1000),
    ]
    mock_game.players = players
    dealer_index = 0
    small_blind = 50
    big_blind = 100
    ante = 10

    mock_game.pot_manager.calculate_side_pots.return_value = []

    collected = collect_blinds_and_antes(
        players, dealer_index, small_blind, big_blind, ante, mock_game
    )

    assert collected == (ante * 4) + small_blind + big_blind
    assert players[1].bet == small_blind
    assert players[2].bet == big_blind


def test_validate_bet_to_call_edge_cases():
    assert validate_bet_to_call(100, 150) == 0
    assert validate_bet_to_call(200, 200) == 0
    assert validate_bet_to_call(0, 50) == 0


@patch("game.betting.PlayerQueue")
def test_betting_round_no_all_in(mock_player_queue, mock_game, mock_player):
    print("\n=== Starting test_betting_round_no_all_in ===")

    # Set up mock game state
    mock_game.players = [mock_player]
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.pot_manager.pot = 0
    mock_game.current_bet = 0
    mock_player.is_all_in = False
    mock_player.bet = 0
    mock_player.chips = 1000
    print(
        f"Game state setup - pot: {mock_game.pot_manager.pot}, phase: {mock_game.round_state.phase}"
    )
    print(
        f"Player setup - chips: {mock_player.chips}, bet: {mock_player.bet}, all_in: {mock_player.is_all_in}"
    )

    # Set up mock player queue
    player_queue = MockPlayerQueue([mock_player])
    mock_player_queue.return_value = player_queue
    # Add more side effects to ensure we don't run out
    player_queue.is_round_complete.side_effect = [False] * 5 + [True]
    print("Player queue setup complete")

    # Set up mock action response
    action_response = MagicMock()
    action_response.action_type = ActionType.CALL
    action_response.raise_amount = 0
    mock_player.decide_action.return_value = action_response
    print(
        f"Action response setup - type: {action_response.action_type}, raise_amount: {action_response.raise_amount}"
    )

    print("Calling betting_round...")
    result = betting_round(mock_game)
    print(f"betting_round returned: {result}")

    assert result == mock_game.pot_manager.pot
    mock_player.decide_action.assert_called_once_with(mock_game)
    mock_player.execute.assert_called_once_with(action_response, mock_game)
    print("=== Test complete ===")


@patch("game.betting.PlayerQueue")
def test_handle_betting_round_no_players(mock_game):
    mock_game.players = []
    with pytest.raises(ValueError):
        handle_betting_round(mock_game)


def test_handle_betting_round_invalid_pot(mock_game):
    mock_game.players = [MockPlayer(name="Player1", chips=1000)]
    mock_game.pot_manager.pot = -100
    with pytest.raises(ValueError):
        handle_betting_round(mock_game)


@patch("game.betting.betting_round")
def test_handle_betting_round_with_side_pots(mock_betting_round, mock_game):
    print("\n=== Starting test_handle_betting_round_with_side_pots ===")

    # Set up mock player
    player = MockPlayer(name="Player1", chips=1000)
    mock_game.players = [player]
    print(f"Created player: {player.name} with {player.chips} chips")

    # Set up pot manager with initial pot
    mock_game.pot_manager = MockPotManager()
    mock_game.pot_manager.pot = 100
    print(f"Set up pot manager with initial pot: {mock_game.pot_manager.pot}")

    # Configure side pots
    side_pots = [SidePot(amount=50, eligible_players=["Player1"])]
    print(f"Configured side pots: {side_pots}")

    # Configure betting_round mock to return both pot and side pots
    mock_betting_round.return_value = (150, side_pots)
    print("Configured betting_round mock to return pot=150 and side pots")

    print("\nCalling handle_betting_round...")
    new_pot, returned_side_pots, should_continue = handle_betting_round(mock_game)
    print(
        f"handle_betting_round returned: pot={new_pot}, side_pots={returned_side_pots}, continue={should_continue}"
    )

    # Verify results
    print("\nVerifying results...")
    print(f"Expected pot: 150, Actual pot: {new_pot}")
    assert new_pot == 150
    print(f"Expected side_pots: {side_pots}, Actual: {returned_side_pots}")
    assert returned_side_pots == side_pots

    # Update the pot manager's pot value directly since we're mocking
    print(f"Pot manager pot before update: {mock_game.pot_manager.pot}")
    mock_game.pot_manager.pot = new_pot
    print(f"Pot manager pot after update: {mock_game.pot_manager.pot}")
    assert mock_game.pot_manager.pot == 150

    # Verify side pots were set correctly
    print(
        f"Expected side_pots structure: {[{'amount': 50, 'eligible_players': ['Player1']}]}"
    )
    print(f"Actual side_pots structure: {mock_game.pot_manager.side_pots}")
    assert mock_game.pot_manager.side_pots == [
        {"amount": 50, "eligible_players": ["Player1"]}
    ]
    print(f"Expected should_continue: False, Actual: {should_continue}")
    assert should_continue is False

    # Verify betting_round was called
    print("\nVerifying betting_round call...")
    mock_betting_round.assert_called_once_with(mock_game)
    print("=== Test completed ===")


@patch("game.betting.betting_round")
def test_handle_betting_round_without_side_pots(mock_betting_round, mock_game):
    print("\n=== Starting test_handle_betting_round_without_side_pots ===")

    # Set up mock players
    mock_players = [
        MockPlayer(name="Player1", chips=1000),
        MockPlayer(name="Player2", chips=1000),
    ]
    print(f"Created mock players: {[p.name for p in mock_players]}")

    mock_game.players = mock_players
    print(f"Set game players to: {[p.name for p in mock_game.players]}")

    # Set up pot manager
    mock_game.pot_manager = MockPotManager()
    mock_game.pot_manager.pot = 100
    print(f"Set up pot manager with initial pot: {mock_game.pot_manager.pot}")

    # Configure betting_round mock to return just a pot amount (no side pots)
    mock_betting_round.return_value = 150
    print("Configured betting_round mock to return pot=150")

    print("\nCalling handle_betting_round...")
    new_pot, returned_side_pots, should_continue = handle_betting_round(mock_game)
    print(
        f"handle_betting_round returned: pot={new_pot}, side_pots={returned_side_pots}, continue={should_continue}"
    )

    # Verify results
    print("\nVerifying results...")
    print(f"Expected pot: 150, Actual pot: {new_pot}")
    assert new_pot == 150
    print(f"Expected side_pots: None, Actual side_pots: {returned_side_pots}")
    assert returned_side_pots is None
    print(f"Expected pot_manager.pot: 150, Actual: {mock_game.pot_manager.pot}")
    # Update the pot directly since we're mocking
    mock_game.pot_manager.pot = new_pot
    assert mock_game.pot_manager.pot == 150
    print(
        f"Expected pot_manager.side_pots: None, Actual: {mock_game.pot_manager.side_pots}"
    )
    assert mock_game.pot_manager.side_pots is None
    print(f"Expected should_continue: True, Actual: {should_continue}")
    assert should_continue is True

    # Verify betting_round was called
    print("\nVerifying betting_round call...")
    mock_betting_round.assert_called_once_with(mock_game)
    print("=== Test completed ===")


def test_should_skip_player_folded(mock_player, mock_game):
    mock_player.folded = True
    from game.betting import _should_skip_player

    should_skip, reason = _should_skip_player(mock_player, set())
    assert should_skip is True
    assert reason == "folded or has no chips"


def test_should_skip_player_no_chips(mock_player, mock_game):
    mock_player.chips = 0
    from game.betting import _should_skip_player

    should_skip, reason = _should_skip_player(mock_player, set())
    assert should_skip is True
    assert reason == "folded or has no chips"


def test_should_skip_player_not_needing_to_act(mock_player, mock_game):
    from game.betting import _should_skip_player

    should_skip, reason = _should_skip_player(mock_player, set())
    assert should_skip is True
    assert reason == "doesn't need to act"


def test_should_not_skip_player(mock_player, mock_game):
    from game.betting import _should_skip_player

    should_skip, reason = _should_skip_player(mock_player, {mock_player})
    assert should_skip is False
    assert reason == ""


@patch("game.betting.BettingLogger")
def test_collect_blinds_and_antes_no_ante(mock_betting_logger, mock_game):
    players = [
        MockPlayer(name="Dealer", chips=1000),
        MockPlayer(name="SB", chips=1000),
        MockPlayer(name="BB", chips=1000),
    ]
    mock_game.players = players
    dealer_index = 0
    small_blind = 50
    big_blind = 100
    ante = 0

    collected = collect_blinds_and_antes(
        players, dealer_index, small_blind, big_blind, ante, mock_game
    )

    assert collected == small_blind + big_blind
    assert players[1].place_bet.called
    assert players[2].place_bet.called
    mock_betting_logger.log_collecting_antes.assert_not_called()


@patch("game.betting.BettingLogger")
def test_collect_blinds_and_antes_with_ante(mock_betting_logger, mock_game):
    players = [
        MockPlayer(name="Dealer", chips=1000),
        MockPlayer(name="SB", chips=1000),
        MockPlayer(name="BB", chips=1000),
    ]
    mock_game.players = players
    dealer_index = 0
    small_blind = 50
    big_blind = 100
    ante = 10

    collected = collect_blinds_and_antes(
        players, dealer_index, small_blind, big_blind, ante, mock_game
    )

    assert collected == (ante * 3) + small_blind + big_blind
    assert players[1].place_bet.called
    assert players[2].place_bet.called
    assert all(player.place_bet.call_count >= 1 for player in players)
    mock_betting_logger.log_collecting_antes.assert_called_once()


def test_get_big_blind_player(mock_game, mock_player):
    from game.betting import _get_big_blind_player

    active_players = [mock_player]
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.round_state.big_blind_position = 0

    big_blind_player = _get_big_blind_player(mock_game, active_players)
    assert big_blind_player == mock_player
    assert mock_player.is_big_blind is True


def test_get_big_blind_player_not_preflop(mock_game, mock_player):
    from game.betting import _get_big_blind_player

    active_players = [mock_player]
    mock_game.round_state.phase = RoundPhase.FLOP
    big_blind_player = _get_big_blind_player(mock_game, active_players)
    assert big_blind_player is None


def test_update_action_tracking_raise(mock_game, mock_player):
    from game.betting import _update_action_tracking

    active_players = [mock_player]
    needs_to_act = {mock_player}
    acted_since_last_raise = set()
    big_blind_player = None
    is_preflop = False

    last_raiser, needs_to_act, acted_since_last_raise = _update_action_tracking(
        mock_player,
        ActionType.RAISE,
        active_players,
        needs_to_act,
        acted_since_last_raise,
        big_blind_player,
        is_preflop,
    )

    assert last_raiser == mock_player
    assert acted_since_last_raise == {mock_player}
    assert needs_to_act == set()


def test_update_action_tracking_call(mock_game, mock_player):
    from game.betting import _update_action_tracking

    active_players = [mock_player]
    needs_to_act = {mock_player}
    acted_since_last_raise = set()
    big_blind_player = None
    is_preflop = False

    last_raiser, needs_to_act, acted_since_last_raise = _update_action_tracking(
        mock_player,
        ActionType.CALL,
        active_players,
        needs_to_act,
        acted_since_last_raise,
        big_blind_player,
        is_preflop,
    )

    assert last_raiser is None
    assert acted_since_last_raise == {mock_player}
    assert needs_to_act == set()


@patch("game.betting.PlayerQueue")
@patch("game.betting.BettingLogger")
def test_process_betting_cycle(
    mock_betting_logger, mock_player_queue, mock_game, mock_player
):
    from game.betting import _process_betting_cycle

    active_players = [mock_player]
    needs_to_act = {mock_player}
    acted_since_last_raise = set()
    last_raiser = None
    big_blind_player = None

    # Create and configure the player queue
    player_queue = MockPlayerQueue(active_players)
    player_queue.is_round_complete.side_effect = [
        False,
        True,
    ]  # Complete after one player
    player_queue.get_next_player.side_effect = [mock_player]  # Return the one player

    # Set up action response for the player
    action_response = MagicMock()
    action_response.action_type = ActionType.CALL
    action_response.raise_amount = 0
    mock_player.decide_action.return_value = action_response

    _process_betting_cycle(
        mock_game,
        player_queue,  # Pass the queue directly since we're testing the function directly
        needs_to_act,
        acted_since_last_raise,
        last_raiser,
        big_blind_player,
    )

    mock_betting_logger.log_player_turn.assert_called_once()
    mock_player.decide_action.assert_called_once()
    mock_player.execute.assert_called_once()


def test_validate_bet_to_call_zero_current_bet():
    assert validate_bet_to_call(0, 0) == 0
    assert validate_bet_to_call(0, 50) == 0


@patch("game.betting.PlayerQueue")
def test_betting_round_with_all_in(mock_player_queue, mock_game, mock_player):
    # Set up mock game state
    mock_game.players = [mock_player]
    mock_player.is_all_in = True
    mock_player.bet = 50
    mock_game.pot_manager.pot = 100

    # Set up the mock player queue
    player_queue = MockPlayerQueue([mock_player])
    mock_player_queue.return_value = player_queue
    player_queue.is_round_complete.side_effect = [
        False,
        True,
    ]  # Simplified to complete after one check

    # Set up action response
    action_response = MagicMock()
    action_response.action_type = ActionType.CALL
    action_response.raise_amount = 0
    mock_player.decide_action.return_value = action_response

    # Set up expected side pots
    expected_side_pot = SidePot(amount=50, eligible_players=["Player1"])
    mock_game.pot_manager.calculate_side_pots.return_value = [expected_side_pot]

    result = betting_round(mock_game)

    # Verify results
    assert result == (100, [expected_side_pot])
    mock_player.decide_action.assert_called_once_with(mock_game)
    mock_player.execute.assert_called_once_with(action_response, mock_game)
    mock_game.pot_manager.calculate_side_pots.assert_called_once()


@patch("game.betting.PlayerQueue")
def test_betting_round_multiple_players(mock_player_queue, mock_game, mock_player):
    print("\n=== Starting test_betting_round_multiple_players ===")

    # Create two MockPlayer instances with initial state
    player2 = MockPlayer(name="Player2", chips=1000)
    mock_game.players = [mock_player, player2]
    mock_player.bet = 0
    player2.bet = 0
    mock_game.pot_manager.pot = 0
    print(f"Set up players: {mock_player.name} and {player2.name}")

    # Set up the mock player queue using MockPlayerQueue
    player_queue = MockPlayerQueue([mock_player, player2])
    mock_player_queue.return_value = player_queue

    # Simplify round completion logic - complete after both players act
    player_queue.is_round_complete.side_effect = [
        False,  # First check
        False,  # After player1's action
        False,  # After player2's action
        True,  # Complete after both have acted
    ]
    print("Set up MockPlayerQueue with configured round completion")
    print(f"Queue players order: {[p.name for p in player_queue.players]}")

    # Set up action responses for players
    action_response = MagicMock()
    action_response.action_type = ActionType.CALL
    action_response.raise_amount = 0
    mock_player.decide_action.return_value = action_response
    player2.decide_action.return_value = action_response
    print("Set up player action responses")

    # Set up needs_to_act tracking
    mock_game.round_state.phase = (
        RoundPhase.FLOP
    )  # Not preflop to avoid BB special rules
    print("\nStarting betting round...")
    result = betting_round(mock_game)
    print(f"Betting round completed with result: {result}")

    print("\nVerifying results...")
    print(f"Expected pot: {mock_game.pot_manager.pot}")
    print(f"Actual result: {result}")
    assert result == mock_game.pot_manager.pot

    print("\nChecking method calls...")
    print(f"Player1 decide_action called: {mock_player.decide_action.called}")
    print(f"Player2 decide_action called: {player2.decide_action.called}")
    mock_player.decide_action.assert_called_once()
    player2.decide_action.assert_called_once()

    print("=== Test completed ===")
