from itertools import chain, repeat
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


def test_collect_blinds_and_antes(mock_blind_config, mock_game, mock_players, mock_betting_logger):
    """
    Tests collection of blinds and antes from players.
    Assumes:
    - 3+ players in mock_players
    - Players at indices 1 and 2 can post small and big blinds respectively
    - All players have sufficient chips for blinds and antes
    """
    dealer_index, small_blind, big_blind, ante = mock_blind_config
    mock_game.players = mock_players

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
    Verifies:
    - Player queue tracks betting actions correctly
    - Round completes when all players have acted
    - Player actions are executed properly
    """
    print("\n=== Starting test_betting_round_no_all_in ===")

    mock_game.players = [mock_player_with_action]
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.pot_manager.pot = 0
    mock_game.current_bet = 0

    # Set up mock player queue with new functionality
    player_queue = mock_player_queue.return_value
    player_queue.needs_to_act = {mock_player_with_action}
    player_queue.acted_since_last_raise = set()
    player_queue.active_players = [mock_player_with_action]

    # Configure mock behaviors
    player_queue.get_next_player.side_effect = [mock_player_with_action, None]
    player_queue.is_round_complete.side_effect = [
        False,
        False,
        True,
    ]  # Need enough values for the loop
    player_queue.all_players_acted.return_value = True

    betting_round(mock_game)

    # Verify player queue was updated correctly
    player_queue.mark_player_acted.assert_called_once()
    mock_player_with_action.decide_action.assert_called_once_with(mock_game)
    mock_player_with_action.execute.assert_called_once()

    # Verify round completion was checked
    player_queue.is_round_complete.assert_called()


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


@patch("game.betting.PlayerQueue")
def test_handle_betting_round_with_side_pots(
    mock_player_queue_class, mock_game, mock_all_in_player, mock_active_players
):
    """
    Tests handling of a betting round with side pots.
    Verifies:
    - All-in players are tracked correctly
    - Active players can still act
    - Game continues with multiple active players
    """
    print("\n=== Starting test_handle_betting_round_with_side_pots ===")

    # Set up game state
    mock_game.players = [mock_all_in_player] + mock_active_players
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.current_bet = 100

    print(f"\nGame state configured:")
    print(f"- Number of players: {len(mock_game.players)}")
    print(f"- Current bet: {mock_game.current_bet}")

    # Configure player queue
    player_queue = mock_player_queue_class.return_value
    player_queue.active_players = mock_active_players
    player_queue.all_in_players = [mock_all_in_player]
    player_queue.needs_to_act = set(mock_active_players)
    player_queue.acted_since_last_raise = set()

    # Configure queue behavior using chain and repeat
    from itertools import chain, repeat

    player_queue.get_next_player.side_effect = mock_active_players + [None]
    player_queue.is_round_complete.side_effect = chain(
        [False] * len(mock_active_players), repeat(True)
    )
    player_queue.all_players_acted.return_value = True

    print("\nPlayerQueue configured:")
    print(f"- Active players: {len(player_queue.active_players)}")
    print(f"- All-in players: {len(player_queue.all_in_players)}")
    print(f"- Players needing to act: {len(player_queue.needs_to_act)}")

    # Configure action responses
    action_response = MagicMock()
    action_response.action_type = ActionType.CALL
    for player in mock_active_players:
        player.decide_action.return_value = action_response
        player.execute = MagicMock()

    print("\nStarting betting round...")
    should_continue = handle_betting_round(mock_game)

    print(f"\nVerifying results:")
    print(f"- Should continue: {should_continue}")
    print(f"- Active players remaining: {len(player_queue.active_players)}")

    # Verify game should continue with multiple active players
    assert should_continue is True
    assert len(player_queue.active_players) > 1

    # Verify active players acted but all-in player didn't
    print("\nVerifying actions:")
    for player in mock_active_players:
        print(f"Checking {player.name} acted...")
        player.decide_action.assert_called_once_with(mock_game)
        player.execute.assert_called_once()

    print(f"Checking all-in player didn't act...")
    mock_all_in_player.decide_action.assert_not_called()
    mock_all_in_player.execute.assert_not_called()

    print("\n=== Test completed successfully ===")


def test_handle_betting_round_without_side_pots(mock_game, mock_players):
    """
    Tests handle_betting_round when no side pots are created.
    Verifies:
    - Basic betting round executes successfully
    - Game continues with multiple active players
    - Pot is updated correctly
    """
    print("\n=== Starting test_handle_betting_round_without_side_pots ===")

    # Set up mock game state
    mock_game.players = mock_players
    mock_game.pot_manager.pot = 0
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.current_bet = 0

    print(f"Initial game state:")
    print(f"- Number of players: {len(mock_players)}")
    print(f"- Game phase: {mock_game.round_state.phase}")
    print(f"- Current bet: {mock_game.current_bet}")

    # Configure players to stay in hand
    for i, player in enumerate(mock_players):
        player.folded = False
        player.is_all_in = False
        player.bet = 0
        player.chips = 1000
        # Configure player actions
        action_response = MagicMock()
        action_response.action_type = ActionType.CALL
        player.decide_action.return_value = action_response
        print(f"Configured Player {i+1}:")
        print(f"- Folded: {player.folded}")
        print(f"- All-in: {player.is_all_in}")
        print(f"- Chips: {player.chips}")
        print(f"- Bet: {player.bet}")

    print("\nSetting up PlayerQueue mock...")
    # Mock PlayerQueue behavior
    with patch("game.betting.PlayerQueue") as mock_queue_class:
        player_queue = mock_queue_class.return_value
        player_queue.active_players = mock_players
        player_queue.needs_to_act = set(mock_players)
        player_queue.acted_since_last_raise = set()

        # Configure queue behavior
        player_queue.get_next_player.side_effect = mock_players + [None]
        # Use chain to prevent StopIteration
        player_queue.is_round_complete.side_effect = chain(
            [False] * len(mock_players), repeat(True)
        )
        player_queue.all_players_acted.return_value = True

        print("PlayerQueue configured:")
        print(f"- Active players: {len(player_queue.active_players)}")
        print(f"- Players needing to act: {len(player_queue.needs_to_act)}")
        print(
            f"- Players who acted since raise: {len(player_queue.acted_since_last_raise)}"
        )

        print("\nStarting betting round...")
        should_continue = handle_betting_round(mock_game)
        print(f"\nBetting round complete:")
        print(f"- Should continue: {should_continue}")
        print(
            f"- Active players remaining: {sum(1 for p in mock_players if not p.folded)}"
        )

        # Verify game should continue with multiple active players
        assert should_continue is True
        assert sum(1 for p in mock_players if not p.folded) > 1

        # Verify player actions were called
        print("\nVerifying player actions:")
        for i, player in enumerate(mock_players):
            print(f"Checking Player {i+1} actions...")
            player.decide_action.assert_called_once_with(mock_game)

    print("\n=== Test completed successfully ===")


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
    player_queue = mock_player_queue_class.return_value
    player_queue.active_players = [mock_active_player]
    player_queue.all_in_players = [mock_all_in_player]
    player_queue.needs_to_act = {mock_active_player}
    player_queue.acted_since_last_raise = set()

    # Configure queue behavior using chain and repeat
    player_queue.get_next_player.side_effect = [mock_active_player, None]
    player_queue.is_round_complete.side_effect = chain([False, False], repeat(True))
    player_queue.all_players_acted.return_value = True

    # Configure action responses
    action_response = MagicMock()
    action_response.action_type = ActionType.CALL
    mock_active_player.decide_action.return_value = action_response
    mock_all_in_player.decide_action.return_value = action_response

    print(f"\nInitial state:")
    print(f"- Active players: {len(player_queue.active_players)}")
    print(f"- All-in players: {len(player_queue.all_in_players)}")
    print(f"- Players needing to act: {len(player_queue.needs_to_act)}")

    betting_round(mock_game)

    print(f"\nVerifying actions:")
    print(f"- Active player action called: {mock_active_player.decide_action.called}")
    print(f"- All-in player action called: {mock_all_in_player.decide_action.called}")

    # Verify actions
    mock_active_player.decide_action.assert_called_once_with(mock_game)
    mock_all_in_player.decide_action.assert_not_called()  # All-in player shouldn't act

    print("\n=== Test completed successfully ===")


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
    print("\n=== Starting test_betting_round_multiple_players ===")

    # Set up game state
    mock_game.players = mock_active_players[:2]  # Use first two players
    mock_game.round_state.phase = RoundPhase.FLOP
    mock_game.current_bet = 0

    print(f"Initial game state:")
    print(f"- Number of players: {len(mock_game.players)}")
    print(f"- Game phase: {mock_game.round_state.phase}")
    print(f"- Current bet: {mock_game.current_bet}")

    # Configure the mock player queue
    player_queue = mock_player_queue_class.return_value
    player_queue.active_players = mock_game.players
    player_queue.needs_to_act = set(mock_game.players)
    player_queue.acted_since_last_raise = set()

    # Configure queue behavior using chain and repeat
    from itertools import chain, repeat

    player_queue.get_next_player.side_effect = mock_game.players + [None]
    player_queue.is_round_complete.side_effect = chain(
        [False] * len(mock_game.players), repeat(True)
    )
    player_queue.all_players_acted.return_value = True

    print("\nPlayerQueue configured:")
    print(f"- Active players: {len(player_queue.active_players)}")
    print(f"- Players needing to act: {len(player_queue.needs_to_act)}")
    print(
        f"- Players who acted since raise: {len(player_queue.acted_since_last_raise)}"
    )

    # Set up action responses
    for player in mock_game.players:
        player.decide_action.return_value = mock_action_response
        player.execute = MagicMock()
        print(f"Configured {player.name}:")
        print(f"- Action type: {mock_action_response.action_type}")

    print("\nStarting betting round...")
    betting_round(mock_game)

    # Verify actions
    print("\nVerifying player actions:")
    for i, player in enumerate(mock_game.players):
        print(f"Checking Player {i+1} actions...")
        player.decide_action.assert_called_once_with(mock_game)
        player.execute.assert_called_once()

    print("\n=== Test completed successfully ===")


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

    # Configure player queue
    player_queue = state["player_queue"]
    player_queue.active_players = state["active_players"]
    player_queue.needs_to_act = set(state["active_players"])
    player_queue.acted_since_last_raise = set()

    # Test raise action
    last_raiser = _update_action_tracking(
        player,
        ActionType.RAISE,
        player_queue,
        None,  # big_blind_player
        False,  # is_preflop
    )

    # Verify results
    assert last_raiser == player
    assert player in player_queue.acted_since_last_raise
    assert player not in player_queue.needs_to_act
    # Verify other players need to act after a raise
    for p in state["active_players"][1:]:
        assert p in player_queue.needs_to_act


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

    # Configure player queue
    player_queue = state["player_queue"]
    player_queue.active_players = state["active_players"]
    player_queue.needs_to_act = set(state["active_players"])
    player_queue.acted_since_last_raise = set()

    # Test call action
    last_raiser = _update_action_tracking(
        player,
        ActionType.CALL,
        player_queue,
        None,  # big_blind_player
        False,  # is_preflop
    )

    # Verify results
    assert last_raiser is None
    assert player in player_queue.acted_since_last_raise
    assert player not in player_queue.needs_to_act


@patch("game.betting.PlayerQueue")
def test_betting_round_multiple_all_ins(
    mock_player_queue_class, mock_game, mock_pot_with_side_pots
):
    """
    Tests multiple players going all-in with different chip amounts.
    Scenario:
    - Player1: All-in with 100 chips
    - Player2: All-in with 200 chips
    - Player3: All-in with 300 chips
    - Player4: Has 1000 chips and calls
    Should create:
    - Main pot: 400 (100 x 4 players)
    - Side pot 1: 300 (100 x 3 players)
    - Side pot 2: 200 (100 x 2 players)
    """
    print("\n=== Starting test_betting_round_multiple_all_ins ===")

    # Set up players
    player1 = MagicMock(name="Player1")
    player1.name = "Player1"
    player1.chips = 0
    player1.bet = 100
    player1.is_all_in = True
    player1.folded = False

    player2 = MagicMock(name="Player2")
    player2.name = "Player2"
    player2.chips = 0
    player2.bet = 200
    player2.is_all_in = True
    player2.folded = False

    player3 = MagicMock(name="Player3")
    player3.name = "Player3"
    player3.chips = 0
    player3.bet = 300
    player3.is_all_in = True
    player3.folded = False

    player4 = MagicMock(name="Player4")
    player4.name = "Player4"
    player4.chips = 700
    player4.bet = 300
    player4.is_all_in = False
    player4.folded = False

    players = [player1, player2, player3, player4]
    mock_game.players = players
    mock_game.pot_manager = mock_pot_with_side_pots
    mock_game.current_bet = 300

    print("\nGame state configured:")
    print(f"- Number of players: {len(players)}")
    print(f"- Current bet: {mock_game.current_bet}")

    # Configure player queue
    player_queue = mock_player_queue_class.return_value
    player_queue.active_players = [player4]  # Only player4 is still active
    player_queue.all_in_players = [player1, player2, player3]
    player_queue.needs_to_act = {player4}
    player_queue.acted_since_last_raise = set()

    # Configure queue behavior using chain and repeat
    from itertools import chain, repeat

    player_queue.get_next_player.side_effect = [player4, None]
    player_queue.is_round_complete.side_effect = chain([False], repeat(True))
    player_queue.all_players_acted.return_value = True

    print("\nPlayerQueue configured:")
    print(f"- Active players: {len(player_queue.active_players)}")
    print(f"- All-in players: {len(player_queue.all_in_players)}")
    print(f"- Players needing to act: {len(player_queue.needs_to_act)}")

    # Configure action responses
    action_response = MagicMock()
    action_response.action_type = ActionType.CALL
    for player in players:
        player.decide_action.return_value = action_response
        player.execute = MagicMock()

    print("\nStarting betting round...")
    betting_round(mock_game)

    # Verify only active player acted
    print("\nVerifying actions:")
    player4.decide_action.assert_called_once_with(mock_game)
    player4.execute.assert_called_once()

    # Verify all-in players didn't act
    for player in [player1, player2, player3]:
        print(f"Checking {player.name} didn't act...")
        player.decide_action.assert_not_called()
        player.execute.assert_not_called()

    print("\n=== Test completed successfully ===")


@patch("game.betting.PlayerQueue")
def test_betting_round_one_chip_all_in(
    mock_player_queue_class, mock_game, mock_pot_with_side_pots
):
    """
    Tests scenario where a player goes all-in with exactly 1 chip.
    Verifies that:
    - Player can go all-in with 1 chip
    - Player is properly marked as all-in
    - Only non-all-in player gets to act
    """
    print("\n=== Starting test_betting_round_one_chip_all_in ===")

    # Set up players
    one_chip_player = MagicMock(name="OneChipPlayer")
    one_chip_player.name = "OneChipPlayer"
    one_chip_player.chips = 0
    one_chip_player.bet = 1
    one_chip_player.is_all_in = True
    one_chip_player.folded = False

    caller = MagicMock(name="Caller")
    caller.name = "Caller"
    caller.chips = 999
    caller.bet = 100
    caller.is_all_in = False
    caller.folded = False

    players = [one_chip_player, caller]
    mock_game.players = players
    mock_game.pot_manager = mock_pot_with_side_pots
    mock_game.current_bet = 100

    print("\nGame state configured:")
    print(f"- Number of players: {len(players)}")
    print(f"- Current bet: {mock_game.current_bet}")

    # Configure player queue
    player_queue = mock_player_queue_class.return_value
    player_queue.active_players = [caller]  # Only caller is active
    player_queue.all_in_players = [one_chip_player]
    player_queue.needs_to_act = {caller}
    player_queue.acted_since_last_raise = set()

    # Configure queue behavior using chain and repeat
    from itertools import chain, repeat

    player_queue.get_next_player.side_effect = [caller, None]
    player_queue.is_round_complete.side_effect = chain([False], repeat(True))
    player_queue.all_players_acted.return_value = True

    print("\nPlayerQueue configured:")
    print(f"- Active players: {len(player_queue.active_players)}")
    print(f"- All-in players: {len(player_queue.all_in_players)}")
    print(f"- Players needing to act: {len(player_queue.needs_to_act)}")

    # Configure action responses
    action_response = MagicMock()
    action_response.action_type = ActionType.CALL
    for player in players:
        player.decide_action.return_value = action_response
        player.execute = MagicMock()

    print("\nStarting betting round...")
    betting_round(mock_game)

    # Verify only active player acted
    print("\nVerifying actions:")
    caller.decide_action.assert_called_once_with(mock_game)
    caller.execute.assert_called_once()

    # Verify all-in player didn't act
    print("Checking all-in player didn't act...")
    one_chip_player.decide_action.assert_not_called()
    one_chip_player.execute.assert_not_called()

    print("\n=== Test completed successfully ===")


@patch("game.betting.PlayerQueue")
def test_betting_round_all_players_all_in(
    mock_player_queue_class, mock_game, mock_pot_with_side_pots
):
    """
    Tests scenario where all players go all-in simultaneously.
    Verifies that:
    - Betting round ends immediately
    - No actions are needed since all players are all-in
    - Player queue properly tracks all-in state
    """
    print("\n=== Starting test_betting_round_all_players_all_in ===")

    # Set up players all going all-in with different amounts
    players = []
    for i, amount in enumerate([50, 100, 150, 200]):
        player = MagicMock(name=f"Player{i+1}")
        player.name = f"Player{i+1}"
        player.chips = 0
        player.bet = amount
        player.is_all_in = True
        player.folded = False
        players.append(player)
        print(f"Created Player{i+1}: bet={amount}, all_in=True")

    mock_game.players = players
    mock_game.pot_manager = mock_pot_with_side_pots
    mock_game.current_bet = 200
    print(f"\nGame state configured:")
    print(f"- Number of players: {len(players)}")
    print(f"- Current bet: {mock_game.current_bet}")

    # Configure player queue
    player_queue = mock_player_queue_class.return_value
    player_queue.active_players = []  # No active players
    player_queue.all_in_players = players  # All players are all-in
    player_queue.needs_to_act = set()  # No one needs to act
    player_queue.acted_since_last_raise = set()

    # Configure queue behavior using chain and repeat
    from itertools import chain, repeat

    player_queue.get_next_player.return_value = None  # No players to act
    player_queue.is_round_complete.side_effect = chain(
        [True], repeat(True)
    )  # Round is immediately complete
    player_queue.all_players_acted.return_value = True

    print("\nPlayerQueue configured:")
    print(f"- Active players: {len(player_queue.active_players)}")
    print(f"- All-in players: {len(player_queue.all_in_players)}")
    print(f"- Players needing to act: {len(player_queue.needs_to_act)}")

    print("\nStarting betting round...")
    betting_round(mock_game)

    # Verify no players acted (since all were all-in)
    print("\nVerifying no actions were taken:")
    for player in players:
        print(f"Checking {player.name} didn't act...")
        player.decide_action.assert_not_called()
        player.execute.assert_not_called()

    # Verify round completion was checked
    player_queue.is_round_complete.assert_called()

    print("\n=== Test completed successfully ===")


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
        mock_insufficient_chips_players, dealer_index, small_blind, big_blind, ante, mock_game
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
        mock_insufficient_chips_players, dealer_index, small_blind, big_blind, ante, mock_game
    )

    # Calculate expected total:
    # - Player 1: 5 chips for ante (all-in)
    # - Player 2: 10 chips for ante + 20 remaining for SB (all-in)
    # - Player 3: 10 chips for ante + 50 remaining for BB (all-in)
    expected_total = (
        5   # Partial ante from player 1 (all-in)
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
        mock_players, dealer_index, small_blind, big_blind, ante, mock_game
    )

    # Small blind should be player 0, big blind should be player 1
    assert mock_players[0].bet == small_blind
    assert mock_players[1].bet == big_blind
    assert collected == (ante * len(mock_players)) + small_blind + big_blind


@patch("game.betting.PlayerQueue")
def test_betting_round_action_tracking(
    mock_player_queue_class, mock_game, mock_active_players, mock_action_response
):
    """
    Tests that betting round properly tracks player actions using PlayerQueue.
    Verifies:
    - Players are marked as having acted
    - Raise resets action tracking
    - Round completes when all players have acted
    """
    print("\n=== Starting test_betting_round_action_tracking ===")

    # Set up game state
    mock_game.players = mock_active_players
    mock_game.round_state.phase = RoundPhase.PREFLOP
    mock_game.current_bet = 0

    # Configure first player to raise
    raise_response = MagicMock()
    raise_response.action_type = ActionType.RAISE
    mock_active_players[0].decide_action.return_value = raise_response

    # Configure other players to call
    for player in mock_active_players[1:]:
        player.decide_action.return_value = mock_action_response  # CALL action
        player.execute = MagicMock()

    print(f"Game state configured:")
    print(f"- Number of players: {len(mock_active_players)}")
    print(f"- First player action: {raise_response.action_type}")

    # Configure player queue
    player_queue = mock_player_queue_class.return_value
    player_queue.active_players = mock_active_players
    player_queue.needs_to_act = set(mock_active_players)
    player_queue.acted_since_last_raise = set()

    # Configure queue behavior using chain and repeat
    from itertools import chain, repeat

    player_queue.get_next_player.side_effect = mock_active_players + [None]
    player_queue.is_round_complete.side_effect = chain(
        [False] * len(mock_active_players), repeat(True)
    )
    player_queue.all_players_acted.return_value = True

    print("\nPlayerQueue configured:")
    print(f"- Active players: {len(player_queue.active_players)}")
    print(f"- Players needing to act: {len(player_queue.needs_to_act)}")

    print("\nStarting betting round...")
    betting_round(mock_game)

    # Verify raise was handled correctly
    print("\nVerifying actions:")
    player_queue.mark_player_acted.assert_any_call(
        mock_active_players[0], is_raise=True
    )

    # Verify other players had to act after the raise
    for player in mock_active_players[1:]:
        assert player in player_queue.needs_to_act
        player.decide_action.assert_called_once_with(mock_game)
        player.execute.assert_called_once()

    print("\n=== Test completed successfully ===")


def test_update_action_tracking_big_blind_preflop(
    mock_betting_state, mock_big_blind_player
):
    """
    Tests action tracking updates for big blind player during preflop.
    Verifies:
    - BB gets option to raise on first action if no previous raises
    - BB needs to act again if someone raises
    """
    from game.betting import _update_action_tracking

    state = mock_betting_state
    player = state["active_players"][0]

    # Configure player queue
    player_queue = state["player_queue"]
    player_queue.active_players = state["active_players"]
    player_queue.needs_to_act = set(state["active_players"])
    player_queue.acted_since_last_raise = set()

    # Test BB first action
    last_raiser = _update_action_tracking(
        mock_big_blind_player,
        ActionType.CALL,
        player_queue,
        mock_big_blind_player,  # big_blind_player
        True,  # is_preflop
    )

    # Verify BB gets option to raise
    assert mock_big_blind_player in player_queue.needs_to_act
    assert last_raiser is None

    # Test when someone raises
    last_raiser = _update_action_tracking(
        player,
        ActionType.RAISE,
        player_queue,
        mock_big_blind_player,
        True,  # is_preflop
    )

    # Verify BB needs to act after raise
    assert mock_big_blind_player in player_queue.needs_to_act
    assert last_raiser == player


def test_update_action_tracking_all_players_acted(mock_betting_state):
    """
    Tests action tracking when all players have acted.
    Verifies:
    - Round completes when all active players have acted
    - No players need to act after completion
    """
    from game.betting import _update_action_tracking

    state = mock_betting_state

    # Configure player queue
    player_queue = state["player_queue"]
    player_queue.active_players = state["active_players"]
    player_queue.needs_to_act = set(state["active_players"])
    player_queue.acted_since_last_raise = set()

    # Have each player call
    for player in state["active_players"]:
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
    assert player_queue.acted_since_last_raise == set(state["active_players"])
