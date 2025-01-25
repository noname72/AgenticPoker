from itertools import chain, repeat
from unittest.mock import MagicMock, patch

import pytest

from data.states.round_state import RoundPhase
from data.types.action_decision import ActionType
from game.betting import betting_round, collect_blinds_and_antes, handle_betting_round
from game.table import Table


@pytest.fixture
def mock_betting_logger():
    """Create a mock betting logger."""
    with patch("game.betting.BettingLogger") as mock_logger:
        mock_logger.log_collecting_antes = MagicMock()
        mock_logger.log_blind_or_ante = MagicMock()
        mock_logger.log_player_turn = MagicMock()
        mock_logger.log_line_break = MagicMock()
        mock_logger.log_debug = MagicMock()
        yield mock_logger


def test_collect_blinds_and_antes(
    mock_blind_config, mock_game, mock_players, mock_betting_logger
):
    """Tests collection of blinds and antes from players."""
    dealer_index, small_blind, big_blind, ante = mock_blind_config
    mock_game.table = Table(mock_players)

    collected = collect_blinds_and_antes(
        mock_game, dealer_index, small_blind, big_blind, ante
    )

    assert collected == (ante * len(mock_players)) + small_blind + big_blind
    assert mock_players[1].bet == small_blind
    assert mock_players[2].bet == big_blind


def test_betting_round_basic_flow(mock_betting_state, player_factory):
    """Tests a basic betting round flow with multiple players."""
    print("\n=== Starting test_betting_round_basic_flow ===")

    # Create players with different actions
    caller = player_factory(name="Caller", action_response=ActionType.CALL)
    raiser = player_factory(name="Raiser", action_response=ActionType.RAISE)
    folder = player_factory(name="Folder", action_response=ActionType.FOLD)

    players = [caller, raiser, folder]

    # Create and configure table
    table = Table(players)
    table.get_next_player = MagicMock(side_effect=[raiser, caller, folder, None])
    table.is_round_complete = MagicMock(
        side_effect=chain(
            [
                (False, "Round continuing"),
                (False, "Round continuing"),
                (True, "All players acted"),
            ]
        )
    )

    # Configure game state
    mock_betting_state["game"].table = table
    mock_betting_state["game"].round_state.phase = RoundPhase.PRE_DRAW
    mock_betting_state["game"].current_bet = 20

    # Run betting round
    betting_round(mock_betting_state["game"])

    # Verify each player acted
    for player in players:
        player.decide_action.assert_called_once_with(mock_betting_state["game"])
        player.execute.assert_called_once()

    # Verify round completion was checked correct number of times
    assert table.is_round_complete.call_count == 3


def test_handle_betting_round_no_players(mock_game):
    """Tests that handle_betting_round raises ValueError when no players exist."""
    mock_game.table = Table([])
    with pytest.raises(ValueError):
        handle_betting_round(mock_game)


def test_handle_betting_round_invalid_pot(mock_game, mock_player):
    """Tests that handle_betting_round raises ValueError with negative pot."""
    mock_game.table = Table([mock_player])
    mock_game.pot.pot = -100
    with pytest.raises(ValueError):
        handle_betting_round(mock_game)


def test_handle_betting_round_continues_multiple_active(mock_game, player_factory):
    """Tests handle_betting_round returns True when multiple players remain active."""
    # Create active players
    active_players = [
        player_factory(name=f"Active{i}", action_response=ActionType.CALL, folded=False)
        for i in range(2)
    ]

    # Set up game state with Table
    mock_game.table = Table(active_players)
    mock_game.pot.pot = 0

    # Run betting round
    should_continue = handle_betting_round(mock_game)

    assert should_continue is True


def test_handle_betting_round_ends_one_active(mock_game, player_factory):
    """Tests handle_betting_round returns False when only one player remains active."""
    # Create one active and one folded player
    active_player = player_factory(name="Active", folded=False)
    folded_player = player_factory(name="Folded", folded=True)

    # Set up game state with Table
    mock_game.table = Table([active_player, folded_player])
    mock_game.pot.pot = 0

    # Run betting round
    should_continue = handle_betting_round(mock_game)

    assert should_continue is False


def test_collect_blinds_and_antes_no_ante(
    mock_game, player_factory, mock_betting_logger
):
    """Tests blind collection when no ante is required."""
    players = [player_factory(name=f"Player{i+1}") for i in range(3)]
    mock_game.table = Table(players)

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


def test_collect_blinds_and_antes_insufficient_chips(
    mock_game, mock_insufficient_chips_players, mock_betting_logger
):
    """Tests collection of blinds when players don't have enough chips."""
    mock_game.table = Table(mock_insufficient_chips_players)

    dealer_index = 0
    small_blind = 50
    big_blind = 100
    ante = 0

    collected = collect_blinds_and_antes(
        mock_game, dealer_index, small_blind, big_blind, ante
    )

    # Verify partial blind payments
    assert mock_insufficient_chips_players[1].bet == 30  # Posted what they could for SB
    assert mock_insufficient_chips_players[2].bet == 60  # Posted what they could for BB
    assert collected == 90  # 30 (partial SB) + 60 (partial BB)


def test_collect_blinds_and_antes_dealer_wrap(
    mock_blind_config, mock_game, mock_players, mock_betting_logger
):
    """Tests blind collection when dealer position causes wrap-around."""
    _, small_blind, big_blind, ante = mock_blind_config
    dealer_index = len(mock_players) - 1  # Override dealer to last player
    mock_game.table = Table(mock_players)

    collected = collect_blinds_and_antes(
        mock_game, dealer_index, small_blind, big_blind, ante
    )

    # Small blind should be player 0, big blind should be player 1
    assert mock_players[0].bet == small_blind
    assert mock_players[1].bet == big_blind
    assert collected == (ante * len(mock_players)) + small_blind + big_blind


def test_betting_round_all_fold(mock_game, player_factory):
    """Tests betting round when all players except one fold."""
    # Create players with actions that will set folded state
    active = player_factory(name="Active", action_response=ActionType.CALL)
    folders = [
        player_factory(name=f"Folder{i}", action_response=ActionType.FOLD)
        for i in range(2)
    ]

    # Configure folder execute methods to set folded state
    for folder in folders:
        # Create closure that captures the specific folder instance
        def make_execute_fold(p):
            def execute_fold(action_decision, game):
                p.folded = True

            return execute_fold

        folder.execute = MagicMock(side_effect=make_execute_fold(folder))

    players = [active] + folders

    # Set up table
    table = Table(players)
    table.get_next_player = MagicMock(side_effect=players + [None])
    table.is_round_complete = MagicMock(
        side_effect=chain(
            [
                (False, "Round continuing"),
                (False, "Round continuing"),
                (True, "Only one player remains"),
            ]
        )
    )

    mock_game.table = table
    betting_round(mock_game)

    # Verify round ended early due to folds
    assert all(p.folded for p in folders)
    assert not active.folded


def test_handle_betting_round_pot_initialization(mock_game, mock_player):
    """Tests pot initialization in handle_betting_round."""
    mock_game.table = Table([mock_player])
    mock_game.pot.pot = None

    handle_betting_round(mock_game)

    assert mock_game.pot.pot == 0


def test_collect_blinds_and_antes_all_in_on_blinds(mock_game, player_factory):
    """Tests blind collection when players go all-in posting blinds."""
    # Create players with exactly enough for small blind and big blind
    sb_player = player_factory(name="SB", chips=10)
    bb_player = player_factory(name="BB", chips=20)
    other = player_factory(name="Other", chips=100)

    # Configure place_bet to set all-in state
    def sb_place_bet(amount, game):
        sb_player.chips = 0
        sb_player.bet = amount
        sb_player.is_all_in = True
        return amount

    def bb_place_bet(amount, game):
        bb_player.chips = 0
        bb_player.bet = amount
        bb_player.is_all_in = True
        return amount

    sb_player.place_bet = MagicMock(side_effect=sb_place_bet)
    bb_player.place_bet = MagicMock(side_effect=bb_place_bet)
    other.place_bet = MagicMock(return_value=0)  # No ante

    players = [other, sb_player, bb_player]
    mock_game.table = Table(players)

    collected = collect_blinds_and_antes(mock_game, 0, 10, 20, 0)

    assert sb_player.chips == 0
    assert bb_player.chips == 0
    assert collected == 30  # 10 SB + 20 BB
    assert sb_player.is_all_in
    assert bb_player.is_all_in
