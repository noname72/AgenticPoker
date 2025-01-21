from itertools import chain, repeat
from unittest.mock import MagicMock, patch

import pytest

from data.states.round_state import RoundPhase
from data.types.action_decision import ActionType
from data.types.pot_types import SidePot
from game.betting import (
    betting_round,
    collect_blinds_and_antes,
    handle_betting_round,
    validate_bet_to_call,
    _get_big_blind_player,
    _should_skip_player,
)


@pytest.fixture
def mock_betting_logger():
    """Create a mock betting logger."""
    with patch("game.betting.BettingLogger") as mock_logger:
        mock_logger.log_collecting_antes = MagicMock()
        mock_logger.log_blind_or_ante = MagicMock()
        mock_logger.log_player_turn = MagicMock()
        mock_logger.log_line_break = MagicMock()
        mock_logger.log_skip_player = MagicMock()
        mock_logger.log_message = MagicMock()  # Add the missing method
        mock_logger.log_state_after_action = MagicMock()  # Add this too for completeness
        yield mock_logger


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


def test_collect_blinds_and_antes(mock_blind_config, mock_game, mock_players, mock_betting_logger):
    """Tests collection of blinds and antes from players."""
    dealer_index, small_blind, big_blind, ante = mock_blind_config
    mock_game.players = mock_players

    collected = collect_blinds_and_antes(
        mock_game, dealer_index, small_blind, big_blind, ante
    )

    assert collected == (ante * len(mock_players)) + small_blind + big_blind
    assert mock_players[1].bet == small_blind
    assert mock_players[2].bet == big_blind


def test_betting_round_no_all_in(mock_betting_state, player_factory):
    """Tests a basic betting round where no players are all-in.
    
    Verifies:
    - Players act in correct order
    - Actions are tracked properly
    - Round completes when all players have acted
    - Betting state is updated correctly
    """
    print("\n=== Starting test_betting_round_no_all_in ===")

    # Create players with different actions
    caller = player_factory(name="Caller", action_response=ActionType.CALL)
    raiser = player_factory(name="Raiser", action_response=ActionType.RAISE)
    folder = player_factory(name="Folder", action_response=ActionType.FOLD)
    
    players = [caller, raiser, folder]
    
    # Configure player queue
    player_queue = mock_betting_state["player_queue"]
    player_queue.players = players  # Set underlying players list
    player_queue.active_players = players
    player_queue.needs_to_act = set(players)
    player_queue.acted_since_last_raise = set()

    # Configure queue behavior - raiser should act first
    player_queue.get_next_player.side_effect = [raiser, caller, folder, None]
    player_queue.is_round_complete.side_effect = chain(
        [False] * len(players), repeat(True)
    )
    player_queue.all_players_acted.return_value = True

    # Configure mark_player_acted to update tracking sets
    def mark_player_acted(player, is_raise=False):
        player_queue.needs_to_act.discard(player)
        if is_raise:
            # Clear acted_since_last_raise and make others need to act
            player_queue.acted_since_last_raise = {player}
            player_queue.needs_to_act.update(p for p in players if p != player)
        else:
            player_queue.acted_since_last_raise.add(player)

    player_queue.mark_player_acted = MagicMock(side_effect=mark_player_acted)

    # Configure game state with player queue
    mock_betting_state["game"].players = player_queue  # Set PlayerQueue instance
    mock_betting_state["game"].round_state.phase = RoundPhase.PREFLOP
    mock_betting_state["game"].current_bet = 20

    # Configure execute methods to update player states
    def execute_action(action_response, game):
        if action_response.action_type == ActionType.FOLD:
            folder.folded = True
        elif action_response.action_type == ActionType.RAISE:
            game.current_bet += 20  # Simple raise amount

    caller.execute = MagicMock(side_effect=lambda a, g: execute_action(a, g))
    raiser.execute = MagicMock(side_effect=lambda a, g: execute_action(a, g))
    folder.execute = MagicMock(side_effect=lambda a, g: execute_action(a, g))

    # Run betting round
    betting_round(mock_betting_state["game"])

    # Verify each player acted exactly once
    for player in players:
        player.decide_action.assert_called_once_with(mock_betting_state["game"])
        player.execute.assert_called_once()

    # Verify player states were updated correctly
    assert folder.folded
    assert not caller.folded
    assert not raiser.folded

    # Verify betting tracking was updated correctly
    # After raise, everyone had to act again
    assert raiser in player_queue.acted_since_last_raise  # Raiser acted first
    assert caller in player_queue.acted_since_last_raise  # Called the raise
    assert folder in player_queue.acted_since_last_raise  # Folded to the raise

    # Verify round completion
    assert len(player_queue.needs_to_act) == 0


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
    mock_game, mock_player_queue, player_factory
):
    """Tests handling of a betting round with side pots."""
    print("\n=== Starting test_handle_betting_round_with_side_pots ===")

    # Create players using factory
    all_in_player = player_factory(
        name="AllInPlayer", chips=0, bet=1000, is_all_in=True
    )

    active_players = [
        player_factory(name=f"Active{i}", action_response=ActionType.CALL)
        for i in range(2)
    ]

    # Set up game state
    mock_game.players = mock_player_queue  # Set PlayerQueue instance directly
    mock_game.players.players = [all_in_player] + active_players  # Set underlying players list
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.current_bet = 100

    print(f"\nGame state configured:")
    print(f"- Number of players: {len(mock_game.players.players)}")
    print(f"- Current bet: {mock_game.current_bet}")

    # Configure player queue behavior
    mock_game.players.active_players = active_players
    mock_game.players.all_in_players = [all_in_player]
    mock_game.players.needs_to_act = set(active_players)
    mock_game.players.acted_since_last_raise = set()

    # Configure queue behavior
    mock_game.players.get_next_player.side_effect = active_players + [None]
    mock_game.players.is_round_complete.side_effect = chain(
        [False] * len(active_players), repeat(True)
    )
    mock_game.players.all_players_acted.return_value = True

    print("\nStarting betting round...")
    should_continue = handle_betting_round(mock_game)

    # Verify game should continue with multiple active players
    assert should_continue is True
    assert len(mock_game.players.active_players) > 1

    # Verify active players acted but all-in player didn't
    for player in active_players:
        player.decide_action.assert_called_once_with(mock_game)
        player.execute.assert_called_once()

    all_in_player.decide_action.assert_not_called()
    all_in_player.execute.assert_not_called()


def test_handle_betting_round_without_side_pots(mock_game, mock_player_queue, player_factory):
    """Tests handle_betting_round when no side pots are created."""
    print("\n=== Starting test_handle_betting_round_without_side_pots ===")

    # Create players using factory
    players = [
        player_factory(name=f"Player{i+1}", action_response=ActionType.CALL)
        for i in range(3)
    ]

    # Set up mock game state
    mock_game.players = mock_player_queue  # Use mock_player_queue instead of list
    mock_game.players.players = players  # Set underlying players list
    mock_game.pot_manager.pot = 0
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.current_bet = 0

    # Configure player queue behavior
    mock_game.players.active_players = players
    mock_game.players.needs_to_act = set(players)
    mock_game.players.acted_since_last_raise = set()

    # Configure queue behavior
    mock_game.players.get_next_player.side_effect = players + [None]
    mock_game.players.is_round_complete.side_effect = chain(
        [False] * len(players), repeat(True)
    )
    mock_game.players.all_players_acted.return_value = True

    should_continue = handle_betting_round(mock_game)

    # Verify game should continue with multiple active players
    assert should_continue is True
    assert sum(1 for p in players if not p.folded) > 1

    # Verify player actions were called
    for player in players:
        player.decide_action.assert_called_once_with(mock_game)


def test_should_skip_player_folded(player_factory):
    """Tests that _should_skip_player correctly identifies folded players."""
    player = player_factory(name="FoldedPlayer", folded=True)
    should_skip, reason = _should_skip_player(player, set())
    assert should_skip is True
    assert reason == "folded"


def test_should_skip_player_no_chips(player_factory):
    """Tests that _should_skip_player correctly identifies players with no chips."""
    player = player_factory(name="BrokePlayer", chips=0)
    should_skip, reason = _should_skip_player(player, set())
    assert should_skip is True
    assert reason == "has no chips"


def test_should_skip_player_not_needing_to_act(player_factory):
    """Tests that _should_skip_player identifies players not needing to act."""
    player = player_factory(name="InactivePlayer")
    should_skip, reason = _should_skip_player(player, set())
    assert should_skip is True
    assert reason == "doesn't need to act"


def test_should_not_skip_player(player_factory):
    """Tests that _should_skip_player identifies players who should act."""
    player = player_factory(name="ActivePlayer")
    should_skip, reason = _should_skip_player(player, {player})
    assert should_skip is False
    assert reason == ""


def test_collect_blinds_and_antes_no_ante(
    mock_game, player_factory, mock_betting_logger
):
    """Tests blind collection when no ante is required."""
    players = [player_factory(name=f"Player{i+1}") for i in range(3)]

    mock_game.players = players
    dealer_index = 0
    small_blind = 50
    big_blind = 100
    ante = 0

    collected = collect_blinds_and_antes(
        mock_game, dealer_index, small_blind, big_blind, ante
    )

    assert collected == small_blind + big_blind
    assert players[1].place_bet.called  # Small blind
    assert players[2].place_bet.called  # Big blind
    mock_betting_logger.log_collecting_antes.assert_not_called()


def test_get_big_blind_player(mock_game, player_factory):
    """Tests identification of big blind player."""
    big_blind_player = player_factory(name="BigBlind", is_big_blind=True)
    mock_game.players = [big_blind_player]
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.round_state.big_blind_position = 0

    result = _get_big_blind_player(mock_game)
    assert result == big_blind_player
    assert big_blind_player.is_big_blind is True


def test_betting_round_with_all_in(
    mock_game, mock_player_queue, mock_pot_with_side_pots, player_factory
):
    """Tests a complex betting round involving an all-in player."""
    print("\n=== Starting test_betting_round_with_all_in ===")

    # Create players using factory
    all_in_player = player_factory(
        name="AllInPlayer", chips=0, bet=1000, is_all_in=True
    )

    active_player = player_factory(
        name="ActivePlayer", chips=500, bet=1500, action_response=ActionType.CALL
    )

    # Set up game state
    mock_game.players = mock_player_queue
    mock_game.players.players = [all_in_player, active_player]
    mock_game.pot_manager = mock_pot_with_side_pots
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.current_bet = 1500

    # Configure player queue behavior
    mock_game.players.active_players = [active_player]
    mock_game.players.all_in_players = [all_in_player]
    mock_game.players.needs_to_act = {active_player}
    mock_game.players.acted_since_last_raise = set()

    # Configure queue behavior
    mock_game.players.get_next_player.side_effect = [active_player, None]
    mock_game.players.is_round_complete.side_effect = chain([False, False], repeat(True))
    mock_game.players.all_players_acted.return_value = True

    print("\nStarting betting round...")
    betting_round(mock_game)

    # Verify actions
    active_player.decide_action.assert_called_once_with(mock_game)
    all_in_player.decide_action.assert_not_called()  # All-in player shouldn't act


def test_betting_round_action_tracking(
    mock_game, mock_player_queue, player_factory
):
    """Tests betting round action tracking."""
    print("\n=== Starting test_betting_round_action_tracking ===")

    # Create players using factory
    raiser = player_factory(name="Raiser", action_response=ActionType.RAISE)
    callers = [
        player_factory(name=f"Caller{i}", action_response=ActionType.CALL)
        for i in range(2)
    ]
    players = [raiser] + callers

    # Set up game state
    mock_game.players = mock_player_queue
    mock_game.players.players = players
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.current_bet = 0

    # Configure player queue behavior
    mock_game.players.active_players = players
    mock_game.players.needs_to_act = set(players)
    mock_game.players.acted_since_last_raise = set()

    # Configure mark_player_acted to update tracking sets correctly
    def mark_player_acted(player, is_raise=False):
        mock_game.players.needs_to_act.discard(player)
        if is_raise:
            # Clear acted_since_last_raise and make others need to act
            mock_game.players.acted_since_last_raise = {player}
            mock_game.players.needs_to_act.update(p for p in players if p != player)
        else:
            mock_game.players.acted_since_last_raise.add(player)

    mock_game.players.mark_player_acted = MagicMock(side_effect=mark_player_acted)

    # Configure queue behavior
    mock_game.players.get_next_player.side_effect = players + [None]
    mock_game.players.is_round_complete.side_effect = chain(
        [False] * len(players), repeat(True)
    )
    mock_game.players.all_players_acted.return_value = True

    betting_round(mock_game)

    # Verify raise was handled correctly
    mock_game.players.mark_player_acted.assert_any_call(raiser, is_raise=True)

    # Verify other players had to act after the raise
    for caller in callers:
        caller.decide_action.assert_called_once_with(mock_game)
        caller.execute.assert_called_once()

    # Verify final state
    assert mock_game.players.acted_since_last_raise == set(players)
    assert len(mock_game.players.needs_to_act) == 0

    print("\n=== Test completed successfully ===")


def test_update_action_tracking_raise(mock_betting_state, player_factory):
    """Tests action tracking updates after a raise."""
    from game.betting import _update_action_tracking

    # Create players using factory
    active_players = [player_factory(name=f"Player{i+1}") for i in range(3)]

    # Configure player queue
    player_queue = mock_betting_state["player_queue"]
    player_queue.active_players = active_players
    player_queue.needs_to_act = set(active_players)
    player_queue.acted_since_last_raise = set()

    # Test raise action
    last_raiser = _update_action_tracking(
        active_players[0],
        ActionType.RAISE,
        player_queue,
        None,  # big_blind_player
        False,  # is_preflop
    )

    # Verify results
    assert last_raiser == active_players[0]
    assert active_players[0] in player_queue.acted_since_last_raise
    assert active_players[0] not in player_queue.needs_to_act
    # Verify other players need to act after a raise
    for player in active_players[1:]:
        assert player in player_queue.needs_to_act


def test_update_action_tracking_call(mock_betting_state, player_factory):
    """Tests action tracking updates after a call."""
    from game.betting import _update_action_tracking

    # Create players using factory
    active_players = [player_factory(name=f"Player{i+1}") for i in range(3)]

    # Configure player queue
    player_queue = mock_betting_state["player_queue"]
    player_queue.active_players = active_players
    player_queue.needs_to_act = set(active_players)
    player_queue.acted_since_last_raise = set()

    # Test call action
    last_raiser = _update_action_tracking(
        active_players[0],
        ActionType.CALL,
        player_queue,
        None,  # big_blind_player
        False,  # is_preflop
    )

    # Verify results
    assert last_raiser is None
    assert active_players[0] in player_queue.acted_since_last_raise
    assert active_players[0] not in player_queue.needs_to_act


@patch("game.betting.PlayerQueue")
def test_betting_round_multiple_all_ins(
    mock_game, mock_player_queue, mock_pot_with_side_pots, player_factory
):
    """Tests multiple players going all-in with different chip amounts."""
    print("\n=== Starting test_betting_round_multiple_all_ins ===")

    # Create players using factory
    players = [
        player_factory(
            name=f"Player{i+1}",
            chips=0,
            bet=amount,
            is_all_in=True,
            action_response=ActionType.CALL,
        )
        for i, amount in enumerate([100, 200, 300])
    ]

    # Add one active player
    active_player = player_factory(
        name="Active", chips=700, bet=300, action_response=ActionType.CALL
    )
    players.append(active_player)

    # Set up game state
    mock_game.players = mock_player_queue
    mock_game.players.players = players
    mock_game.pot_manager = mock_pot_with_side_pots
    mock_game.current_bet = 300

    # Configure player queue behavior
    mock_game.players.active_players = [active_player]
    mock_game.players.all_in_players = players[:3]  # First 3 players are all-in
    mock_game.players.needs_to_act = {active_player}
    mock_game.players.acted_since_last_raise = set()

    # Configure queue behavior
    mock_game.players.get_next_player.side_effect = [active_player, None]
    mock_game.players.is_round_complete.side_effect = chain([False], repeat(True))
    mock_game.players.all_players_acted.return_value = True

    print("\nStarting betting round...")
    betting_round(mock_game)

    # Verify only active player acted
    active_player.decide_action.assert_called_once_with(mock_game)
    active_player.execute.assert_called_once()

    # Verify all-in players didn't act
    for player in players[:3]:
        player.decide_action.assert_not_called()
        player.execute.assert_not_called()


def test_betting_round_one_chip_all_in(
    mock_game, mock_player_queue, mock_pot_with_side_pots, player_factory
):
    """Tests scenario where a player goes all-in with exactly 1 chip."""
    print("\n=== Starting test_betting_round_one_chip_all_in ===")

    # Create players using factory
    one_chip_player = player_factory(
        name="OneChipPlayer", chips=0, bet=1, is_all_in=True
    )

    caller = player_factory(
        name="Caller", chips=999, bet=100, action_response=ActionType.CALL
    )

    players = [one_chip_player, caller]

    # Set up game state
    mock_game.players = mock_player_queue
    mock_game.players.players = players
    mock_game.pot_manager = mock_pot_with_side_pots
    mock_game.current_bet = 100

    # Configure player queue behavior
    mock_game.players.active_players = [caller]
    mock_game.players.all_in_players = [one_chip_player]
    mock_game.players.needs_to_act = {caller}
    mock_game.players.acted_since_last_raise = set()

    # Configure queue behavior
    mock_game.players.get_next_player.side_effect = [caller, None]
    mock_game.players.is_round_complete.side_effect = chain([False], repeat(True))
    mock_game.players.all_players_acted.return_value = True

    betting_round(mock_game)

    # Verify only active player acted
    caller.decide_action.assert_called_once_with(mock_game)
    caller.execute.assert_called_once()

    # Verify all-in player didn't act
    one_chip_player.decide_action.assert_not_called()
    one_chip_player.execute.assert_not_called()


def test_betting_round_all_players_all_in(
    mock_game, mock_player_queue, mock_pot_with_side_pots, player_factory
):
    """Tests scenario where all players go all-in simultaneously."""
    print("\n=== Starting test_betting_round_all_players_all_in ===")

    # Create all-in players using factory
    players = [
        player_factory(name=f"Player{i+1}", chips=0, bet=amount, is_all_in=True)
        for i, amount in enumerate([50, 100, 150, 200])
    ]

    # Set up game state
    mock_game.players = mock_player_queue
    mock_game.players.players = players
    mock_game.pot_manager = mock_pot_with_side_pots
    mock_game.current_bet = 200

    # Configure player queue behavior
    mock_game.players.active_players = []  # No active players
    mock_game.players.all_in_players = players  # All players are all-in
    mock_game.players.needs_to_act = set()  # No one needs to act
    mock_game.players.acted_since_last_raise = set()

    # Configure queue behavior
    mock_game.players.get_next_player.return_value = None  # No players to act
    mock_game.players.is_round_complete.side_effect = chain([True], repeat(True))
    mock_game.players.all_players_acted.return_value = True

    betting_round(mock_game)

    # Verify no players acted (since all were all-in)
    for player in players:
        player.decide_action.assert_not_called()
        player.execute.assert_not_called()

    # Verify round completion was checked
    mock_game.players.is_round_complete.assert_called()


def test_collect_blinds_and_antes_insufficient_chips(
    mock_blind_config, mock_game, mock_insufficient_chips_players, mock_betting_logger
):
    """
    Tests collection of blinds when players don't have enough chips.
    Verifies:
    - Players post what they can when they can't afford full blind
    - Correct amounts are collected and logged
    - Player states are updated appropriately
    """
    dealer_index, small_blind, big_blind, ante = mock_blind_config
    mock_game.players = mock_insufficient_chips_players
    ante = 0  # Override ante for this test to simplify

    collected = collect_blinds_and_antes(
        mock_game, dealer_index, small_blind, big_blind, ante
    )

    # Verify partial blind payments
    assert mock_insufficient_chips_players[1].bet == 30  # Posted what they could for SB
    assert mock_insufficient_chips_players[2].bet == 60  # Posted what they could for BB
    assert mock_insufficient_chips_players[1].chips == 0
    assert mock_insufficient_chips_players[2].chips == 0
    assert collected == 90  # 30 (partial SB) + 60 (partial BB)

    # Verify betting logger was called correctly
    mock_betting_logger.log_blind_or_ante.assert_any_call(
        mock_insufficient_chips_players[1].name, small_blind, 30, is_small_blind=True
    )
    mock_betting_logger.log_blind_or_ante.assert_any_call(
        mock_insufficient_chips_players[2].name, big_blind, 60
    )


def test_collect_blinds_and_antes_insufficient_ante(
    mock_blind_config, mock_game, mock_insufficient_chips_players, mock_betting_logger
):
    """
    Tests ante collection when players can't afford the full ante.
    Verifies:
    - Players post partial antes when they can't afford full amount
    - Correct total is collected
    - Player states are updated appropriately
    """
    dealer_index, small_blind, big_blind, ante = mock_blind_config
    mock_game.players = mock_insufficient_chips_players

    # First player can only afford partial ante
    mock_insufficient_chips_players[0].chips = 5  # Override to test ante specifically

    collected = collect_blinds_and_antes(
        mock_game, dealer_index, small_blind, big_blind, ante
    )

    # Calculate expected total:
    # - Player 1: 5 chips for ante (all-in)
    # - Player 2: 10 chips for ante + 20 remaining for SB (all-in)
    # - Player 3: 10 chips for ante + 50 remaining for BB (all-in)
    expected_total = (
        5  # Partial ante from player 1 (all-in)
        + 10  # Full ante from player 2
        + 20  # Remaining chips from player 2 for SB
        + 10  # Full ante from player 3
        + 50  # Remaining chips from player 3 for BB
    )
    assert collected == expected_total  # Should be 95
    assert mock_insufficient_chips_players[0].chips == 0
    mock_betting_logger.log_collecting_antes.assert_called_once()


def test_collect_blinds_and_antes_dealer_wrap(
    mock_blind_config, mock_game, mock_players, mock_betting_logger
):
    """
    Tests blind collection when dealer position causes wrap-around.
    Verifies:
    - Correct players post blinds when dealer is near end of player list
    - Blind positions wrap correctly to start of player list
    """
    _, small_blind, big_blind, ante = mock_blind_config
    dealer_index = len(mock_players) - 1  # Override dealer to last player
    mock_game.players = mock_players

    collected = collect_blinds_and_antes(
        mock_game, dealer_index, small_blind, big_blind, ante
    )

    # Small blind should be player 0, big blind should be player 1
    assert mock_players[0].bet == small_blind
    assert mock_players[1].bet == big_blind
    assert collected == (ante * len(mock_players)) + small_blind + big_blind


def test_update_action_tracking_big_blind_preflop(mock_betting_state, player_factory):
    """Tests action tracking updates for big blind player during preflop."""
    from game.betting import _update_action_tracking

    # Create players using factory
    big_blind_player = player_factory(name="BigBlind", is_big_blind=True)

    active_player = player_factory(name="Active")

    # Configure player queue
    player_queue = mock_betting_state["player_queue"]
    player_queue.active_players = [big_blind_player, active_player]
    player_queue.needs_to_act = {big_blind_player, active_player}
    player_queue.acted_since_last_raise = set()

    # Test BB first action
    last_raiser = _update_action_tracking(
        big_blind_player,
        ActionType.CALL,
        player_queue,
        big_blind_player,
        True,  # is_preflop
    )

    # Verify BB gets option to raise
    assert big_blind_player in player_queue.needs_to_act
    assert last_raiser is None

    # Test when someone raises
    last_raiser = _update_action_tracking(
        active_player,
        ActionType.RAISE,
        player_queue,
        big_blind_player,
        True,  # is_preflop
    )

    # Verify BB needs to act after raise
    assert big_blind_player in player_queue.needs_to_act
    assert last_raiser == active_player


def test_update_action_tracking_all_players_acted(mock_betting_state, player_factory):
    """Tests action tracking when all players have acted."""
    from game.betting import _update_action_tracking

    # Create players using factory
    active_players = [player_factory(name=f"Player{i+1}") for i in range(3)]

    # Configure player queue
    player_queue = mock_betting_state["player_queue"]
    player_queue.active_players = active_players
    player_queue.needs_to_act = set(active_players)
    player_queue.acted_since_last_raise = set()

    # Have each player call
    for player in active_players:
        last_raiser = _update_action_tracking(
            player,
            ActionType.CALL,
            player_queue,
            None,  # big_blind_player
            False,  # is_preflop
        )
        assert last_raiser is None

    # Verify round completion
    assert len(player_queue.needs_to_act) == 0
    assert player_queue.acted_since_last_raise == set(active_players)
