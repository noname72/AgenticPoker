import pytest
from unittest.mock import Mock, patch
from data.types.action_decision import ActionDecision, ActionType
from game.betting import betting_round
from data.states.round_state import RoundPhase, RoundState
from loggers.betting_logger import BettingLogger
from itertools import cycle


@patch('game.betting.BettingLogger')
def test_betting_round_raise_and_call(mock_logger, mock_betting_state, player_factory):
    """Test that betting round properly completes after a raise and call.
    
    Scenario:
    1. Alice raises to 200
    2. Bob folds
    3. Charlie folds
    4. Randy calls 200
    5. Betting should complete since all active players have acted
    """
    # Create players using the factory
    alice = player_factory(name="Alice", chips=1000)
    bob = player_factory(name="Bob", chips=1000)
    charlie = player_factory(name="Charlie", chips=1000)
    randy = player_factory(name="Randy", chips=1000)
    mock_players = [alice, bob, charlie, randy]

    # Set up game mock using mock_betting_state
    game = Mock()
    game.round_state = RoundState(
        round_number=1,
        phase=RoundPhase.PRE_DRAW,
        current_bet=100,  # Big blind amount
        raise_count=0
    )
    game.players = mock_betting_state["player_queue"]
    game.players.players = mock_players
    game.players.active_players = mock_players.copy()
    game.players.needs_to_act = set(mock_players)
    game.players.acted_since_last_raise = set()
    
    # Make get_next_player cycle through players indefinitely
    game.players.get_next_player.side_effect = cycle(mock_players)

    # Configure player actions
    alice_action = ActionDecision(action_type=ActionType.RAISE, raise_amount=200)
    bob_action = ActionDecision(action_type=ActionType.FOLD)
    charlie_action = ActionDecision(action_type=ActionType.FOLD)
    randy_action = ActionDecision(action_type=ActionType.CALL)

    alice.decide_action = Mock(return_value=alice_action)
    bob.decide_action = Mock(return_value=bob_action)
    charlie.decide_action = Mock(return_value=charlie_action)
    randy.decide_action = Mock(return_value=randy_action)

    # Mock execute method for each player
    for player in mock_players:
        player.execute = Mock()
        player.is_all_in = False

    # Run betting round
    betting_round(game)

    # Verify actions were taken
    alice.decide_action.assert_called_once()
    bob.decide_action.assert_called_once()
    charlie.decide_action.assert_called_once()
    randy.decide_action.assert_called_once()

    # Verify betting round completed
    assert len(game.players.needs_to_act) == 0, "Betting round should be complete"
    assert alice in game.players.acted_since_last_raise, "Alice should be marked as acted"
    assert randy in game.players.acted_since_last_raise, "Randy should be marked as acted"
    assert bob.folded, "Bob should be marked as folded"
    assert charlie.folded, "Charlie should be marked as folded"

    # Verify bet amounts
    assert alice.bet == 200, "Alice's bet should be 200"
    assert randy.bet == 200, "Randy's bet should be 200"
    assert bob.bet == 0, "Bob's bet should be 0 (folded)"
    assert charlie.bet == 0, "Charlie's bet should be 0 (folded)"

    # Verify logger was called appropriately
    mock_logger.log_player_turn.assert_called()
    mock_logger.log_line_break.assert_called() 