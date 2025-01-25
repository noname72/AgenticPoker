from typing import List
from unittest.mock import MagicMock, patch

import pytest

from data.types.action_decision import ActionDecision, ActionType
from game.betting import betting_round
from game.table import Table
from tests.mocks.mock_agent import MockAgent


@pytest.fixture
def mock_game(game_state):
    """Create a mock game instance with basic state."""
    game = MagicMock()
    game.round_state = game_state.round_state
    game.current_bet = game_state.min_bet
    game.small_blind = game_state.small_blind
    game.big_blind = game_state.big_blind
    return game


@pytest.fixture
def setup_players(player_factory) -> List[MockAgent]:
    """Create a list of mock players with specific behaviors.

    Uses player_factory to create consistent player instances with:
    - Standard names (Alice, Bob, Charlie, Randy)
    - 1000 chips each
    - No initial bets
    - Not folded
    """
    players = [
        player_factory(name="Alice", chips=1000),
        player_factory(name="Bob", chips=1000),
        player_factory(name="Charlie", chips=1000),
        player_factory(name="Randy", chips=1000),
    ]

    # Configure initial states
    for player in players:
        player.bet = 0
        player.folded = False

    return players


@patch("game.betting.BettingLogger")
def test_betting_round_raise_and_call(mock_logger, mock_game, setup_players):
    """Test that betting round correctly completes after raise and call.

    Scenario:
    1. Alice raises to 300
    2. Bob folds
    3. Charlie folds
    4. Randy calls 300
    5. Betting round should complete

    Expected:
    - Betting round should complete after Randy calls
    - needs_to_act should be empty
    - Correct chip counts and bets should be recorded
    """
    # Configure logger mock
    mock_logger.log_debug = MagicMock()
    mock_logger.log_player_turn = MagicMock()
    mock_logger.log_player_action = MagicMock()
    mock_logger.log_state_after_action = MagicMock()
    mock_logger.log_line_break = MagicMock()
    mock_logger.log_message = MagicMock()

    players = setup_players

    # Configure player actions using ActionDecision
    alice_decision = ActionDecision(
        action_type=ActionType.RAISE, raise_amount=300, reasoning="Strong hand"
    )
    bob_decision = ActionDecision(action_type=ActionType.FOLD, reasoning="Weak hand")
    charlie_decision = ActionDecision(
        action_type=ActionType.FOLD, reasoning="Weak hand"
    )
    randy_decision = ActionDecision(
        action_type=ActionType.CALL, reasoning="Decent hand"
    )

    # Configure decisions and executions
    players[0].decide_action = MagicMock(return_value=alice_decision)
    players[0].execute = MagicMock(
        side_effect=lambda d, g: players[0].place_bet(d.raise_amount, g)
    )

    players[1].decide_action = MagicMock(return_value=bob_decision)
    players[1].execute = MagicMock(
        side_effect=lambda d, g: setattr(players[1], "folded", True)
    )

    players[2].decide_action = MagicMock(return_value=charlie_decision)
    players[2].execute = MagicMock(
        side_effect=lambda d, g: setattr(players[2], "folded", True)
    )

    players[3].decide_action = MagicMock(return_value=randy_decision)
    players[3].execute = MagicMock(
        side_effect=lambda d, g: players[3].place_bet(300, g)
    )

    # Set up player queue and pot manager
    table = Table(players)
    mock_game.table = table
    mock_game.pot = MagicMock()
    mock_game.pot.pot = 0

    # Run betting round
    betting_round(mock_game)

    # Verify betting round completed correctly
    assert (
        len(table.needs_to_act) == 0
    ), "needs_to_act should be empty after round completion"

    # Verify player states
    assert players[0].bet == 300, "Alice's bet should be 300"
    assert players[3].bet == 300, "Randy's bet should be 300"
    assert players[1].folded, "Bob should have folded"
    assert players[2].folded, "Charlie should have folded"

    # Verify chip counts
    assert players[0].chips == 700, "Alice should have 700 chips remaining"
    assert players[1].chips == 1000, "Bob should have 1000 chips remaining"
    assert players[2].chips == 1000, "Charlie should have 1000 chips remaining"
    assert players[3].chips == 700, "Randy should have 700 chips remaining"

    # Verify last raiser
    assert table.last_raiser == players[0], "Alice should be the last raiser"


@patch("game.betting.BettingLogger")
def test_betting_round_raise_reraise_call(mock_logger, mock_game, setup_players):
    """Test betting round with raise, re-raise, and call sequence.

    Scenario:
    1. Alice raises to 300
    2. Bob re-raises to 600
    3. Charlie folds
    4. Randy folds
    5. Alice calls 600

    Expected:
    - Betting round should complete after Alice calls
    - needs_to_act should be empty
    - Correct chip counts and bets should be recorded
    """
    # Configure logger mock
    mock_logger.log_debug = MagicMock()
    mock_logger.log_player_turn = MagicMock()
    mock_logger.log_player_action = MagicMock()
    mock_logger.log_state_after_action = MagicMock()
    mock_logger.log_line_break = MagicMock()
    mock_logger.log_message = MagicMock()

    players = setup_players

    # Configure Alice's sequence of actions
    def alice_actions(game):
        if alice_actions.first_action:
            alice_actions.first_action = False
            return ActionDecision(
                action_type=ActionType.RAISE, raise_amount=300, reasoning="Strong hand"
            )
        return ActionDecision(
            action_type=ActionType.CALL, reasoning="Still strong but not raising"
        )

    alice_actions.first_action = True
    players[0].decide_action = MagicMock(side_effect=alice_actions)

    # Fix Alice's execute to handle both raise and call correctly
    def alice_execute(decision, game):
        if decision.action_type == ActionType.RAISE:
            players[0].place_bet(decision.raise_amount, game)
        else:
            # For call, calculate additional amount needed
            amount_to_call = 600 - players[0].bet  # Bob's raise minus current bet
            players[0].place_bet(amount_to_call, game)

    players[0].execute = MagicMock(side_effect=alice_execute)

    # Configure other players' actions
    players[1].decide_action = MagicMock(
        return_value=ActionDecision(
            action_type=ActionType.RAISE, raise_amount=600, reasoning="Stronger hand"
        )
    )
    players[1].execute = MagicMock(
        side_effect=lambda d, g: players[1].place_bet(d.raise_amount, g)
    )

    players[2].decide_action = MagicMock(
        return_value=ActionDecision(action_type=ActionType.FOLD, reasoning="Weak hand")
    )
    players[2].execute = MagicMock(
        side_effect=lambda d, g: setattr(players[2], "folded", True)
    )

    players[3].decide_action = MagicMock(
        return_value=ActionDecision(action_type=ActionType.FOLD, reasoning="Weak hand")
    )
    players[3].execute = MagicMock(
        side_effect=lambda d, g: setattr(players[3], "folded", True)
    )

    # Set up player queue
    table = Table(players)
    mock_game.table = table

    # Run betting round
    betting_round(mock_game)

    # Verify betting round completed correctly
    assert (
        len(table.needs_to_act) == 0
    ), "needs_to_act should be empty after round completion"

    # Verify player states
    assert players[0].bet == 600, "Alice's bet should be 600"
    assert players[1].bet == 600, "Bob's bet should be 600"
    assert players[2].folded, "Charlie should have folded"
    assert players[3].folded, "Randy should have folded"

    # Verify chip counts
    assert players[0].chips == 400, "Alice should have 400 chips remaining"
    assert players[1].chips == 400, "Bob should have 400 chips remaining"
    assert players[2].chips == 1000, "Charlie should have 1000 chips remaining"
    assert players[3].chips == 1000, "Randy should have 1000 chips remaining"

    # Verify last raiser
    assert table.last_raiser == players[1], "Bob should be the last raiser"


@patch("game.betting.BettingLogger")
def test_betting_round_all_checks(mock_logger, mock_game, setup_players):
    """Test betting round where all players check.

    Scenario:
    1. Alice checks
    2. Bob checks
    3. Charlie checks
    4. Randy checks

    Expected:
    - Round completes with no bets placed
    - All players keep original chip counts
    - No last raiser set
    """
    players = setup_players
    check_decision = ActionDecision(action_type=ActionType.CHECK, reasoning="Checking")

    # Configure all players to check
    for player in players:
        player.decide_action = MagicMock(return_value=check_decision)
        player.execute = MagicMock()

    table = Table(players)
    mock_game.table = table
    mock_game.pot = MagicMock()
    mock_game.pot.pot = 0

    betting_round(mock_game)

    # Verify no bets placed
    for player in players:
        assert player.bet == 0, f"{player.name} should have no bet"
        assert player.chips == 1000, f"{player.name} should have all chips"
        assert not player.folded, f"{player.name} should not be folded"

    assert table.last_raiser is None, "No raiser should be set after all checks"
    assert len(table.needs_to_act) == 0, "needs_to_act should be empty"


#! Need to fix the all-in logic first
# @patch("game.betting.BettingLogger")
# def test_betting_round_all_in_scenario(mock_logger, mock_game, setup_players):
#     """Test betting round with an all-in situation."""
#     players = setup_players

#     # Configure Alice's sequence (raise then call all-in)
#     def alice_actions(game):
#         if alice_actions.first_action:
#             alice_actions.first_action = False
#             return ActionDecision(action_type=ActionType.RAISE, raise_amount=300)
#         return ActionDecision(action_type=ActionType.CALL)  # Will call the all-in

#     def alice_execute(decision, game):
#         if decision.action_type == ActionType.RAISE:
#             players[0].place_bet(decision.raise_amount, game)
#             game.table.current_bet = decision.raise_amount
#         else:
#             # For call, calculate additional amount needed
#             amount_to_call = game.table.current_bet - players[0].bet
#             players[0].place_bet(amount_to_call, game)
#             players[0].is_all_in = True

#     alice_actions.first_action = True
#     players[0].decide_action = MagicMock(side_effect=alice_actions)
#     players[0].execute = MagicMock(side_effect=alice_execute)

#     # Bob goes all-in
#     players[1].decide_action = MagicMock(
#         return_value=ActionDecision(action_type=ActionType.RAISE, raise_amount=1000)
#     )
#     def bob_execute(decision, game):
#         players[1].place_bet(decision.raise_amount, game)
#         players[1].is_all_in = True
#         game.table.current_bet = decision.raise_amount  # Update table's current bet
#     players[1].execute = MagicMock(side_effect=bob_execute)

#     # Charlie folds
#     players[2].decide_action = MagicMock(
#         return_value=ActionDecision(action_type=ActionType.FOLD)
#     )
#     players[2].execute = MagicMock(
#         side_effect=lambda d, g: setattr(players[2], "folded", True)
#     )

#     # Randy calls all-in
#     players[3].decide_action = MagicMock(
#         return_value=ActionDecision(action_type=ActionType.CALL)
#     )
#     def randy_execute(decision, game):
#         amount_to_call = game.table.current_bet  # Call the full current bet
#         players[3].place_bet(amount_to_call, game)
#         players[3].is_all_in = True
#     players[3].execute = MagicMock(side_effect=randy_execute)

#     table = Table(players)
#     mock_game.table = table
#     mock_game.pot = MagicMock()
#     mock_game.pot.pot = 0

#     betting_round(mock_game)

#     # Verify final state
#     assert players[0].bet == 1000, "Alice should be all-in"
#     assert players[1].bet == 1000, "Bob should be all-in"
#     assert players[2].folded, "Charlie should have folded"
#     assert players[3].bet == 1000, "Randy should be all-in"

#     assert players[0].chips == 0, "Alice should have no chips left"
#     assert players[1].chips == 0, "Bob should have no chips left"
#     assert players[2].chips == 1000, "Charlie should have original chips"
#     assert players[3].chips == 0, "Randy should have no chips left"

#     assert players[0].is_all_in, "Alice should be marked as all-in"
#     assert players[1].is_all_in, "Bob should be marked as all-in"
#     assert players[3].is_all_in, "Randy should be marked as all-in"

#     assert table.last_raiser == players[1], "Bob should be the last raiser"
#     assert len(table.needs_to_act) == 0, "needs_to_act should be empty"


# @patch("game.betting.BettingLogger")
# def test_betting_round_partial_call_all_in(mock_logger, mock_game, setup_players):
#     """Test betting round where a player must call with fewer chips than the bet.

#     Scenario:
#     1. Alice (1000 chips) raises to 300
#     2. Bob (200 chips) calls all-in with less than the bet
#     3. Charlie folds
#     4. Randy calls 300

#     Expected:
#     - Round completes with Bob all-in for less than the full bet
#     - Correct chip counts and side pot situation
#     """
#     players = setup_players
#     players[1].chips = 200  # Set Bob to have only 200 chips

#     # Alice raises to 300
#     players[0].decide_action = MagicMock(
#         return_value=ActionDecision(action_type=ActionType.RAISE, raise_amount=300)
#     )
#     players[0].execute = MagicMock(
#         side_effect=lambda d, g: players[0].place_bet(300, g)
#     )

#     # Bob calls all-in with 200
#     players[1].decide_action = MagicMock(
#         return_value=ActionDecision(action_type=ActionType.CALL)
#     )
#     players[1].execute = MagicMock(
#         side_effect=lambda d, g: players[1].place_bet(200, g)
#     )

#     # Charlie folds
#     players[2].decide_action = MagicMock(
#         return_value=ActionDecision(action_type=ActionType.FOLD)
#     )
#     players[2].execute = MagicMock(
#         side_effect=lambda d, g: setattr(players[2], "folded", True)
#     )

#     # Randy calls 300
#     players[3].decide_action = MagicMock(
#         return_value=ActionDecision(action_type=ActionType.CALL)
#     )
#     players[3].execute = MagicMock(
#         side_effect=lambda d, g: players[3].place_bet(300, g)
#     )

#     table = Table(players)
#     mock_game.table = table
#     mock_game.pot = MagicMock()
#     mock_game.pot.pot = 0

#     betting_round(mock_game)

#     # Verify final state
#     assert players[0].bet == 300, "Alice should have bet 300"
#     assert players[1].bet == 200, "Bob should have bet all 200 chips"
#     assert players[2].folded, "Charlie should have folded"
#     assert players[3].bet == 300, "Randy should have bet 300"

#     assert players[0].chips == 700, "Alice should have 700 chips left"
#     assert players[1].chips == 0, "Bob should have no chips left"
#     assert players[2].chips == 1000, "Charlie should have original chips"
#     assert players[3].chips == 700, "Randy should have 700 chips left"

#     assert table.last_raiser == players[0], "Alice should be the last raiser"
#     assert len(table.needs_to_act) == 0, "needs_to_act should be empty"
