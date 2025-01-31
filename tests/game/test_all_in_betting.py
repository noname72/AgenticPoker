from unittest.mock import Mock

import pytest

from data.enums import ActionType
from data.types.action_decision import ActionDecision
from game import AgenticPoker
from game.player import Player


@pytest.fixture
def player_factory():
    """Factory fixture to create player instances with custom attributes."""

    def create_player(**kwargs):
        player = Mock(spec=Player)
        # Set default attributes
        default_attrs = {
            "name": "TestPlayer",
            "chips": 1000,
            "bet": 0,
            "folded": False,
            "is_all_in": False,
            "hand": Mock(),
        }
        # Update with provided kwargs
        default_attrs.update(kwargs)
        for key, value in default_attrs.items():
            setattr(player, key, value)

        # Add place_bet method that updates chips and bet
        def place_bet(amount, game=None):
            # Don't let bet exceed available chips
            actual_amount = min(amount, player.chips)
            player.chips -= actual_amount
            # Add to existing bet instead of replacing it
            player.bet += actual_amount
            return actual_amount

        # Add execute method that handles different action types
        def execute(action_decision, game):
            if action_decision.action_type == ActionType.FOLD:
                player.folded = True
            elif action_decision.action_type in (ActionType.CALL, ActionType.RAISE):
                if action_decision.action_type == ActionType.CALL:
                    # Calculate how much more they need to add to match the bet
                    current_bet = (
                        game.current_bet if game else action_decision.raise_amount
                    )
                    to_call = current_bet - player.bet
                    # Limit to available chips
                    action_decision.raise_amount = min(to_call, player.chips)

                place_bet(action_decision.raise_amount, game)
                if player.chips == 0:
                    player.is_all_in = True

        player.place_bet = place_bet
        player.execute = execute
        return player

    return create_player


def test_must_call_full_all_in_amount(player_factory):
    """Test that players must call the full all-in amount to continue."""
    # Create players
    alice = player_factory(name="Alice", chips=1000)
    bob = player_factory(name="Bob", chips=1000)
    charlie = player_factory(name="Charlie", chips=1000)

    # Initialize game
    game = AgenticPoker(players=[alice, bob, charlie])

    # Simulate pre-flop action:
    # Alice raises to 510
    alice_raise = ActionDecision(action_type=ActionType.RAISE, raise_amount=510)
    alice.execute(alice_raise, game)
    game.current_bet = 510
    game.pot.add_to_pot(510)
    game.table.update(alice_raise, alice)

    # Bob folds
    bob_fold = ActionDecision(action_type=ActionType.FOLD, raise_amount=0)
    bob.execute(bob_fold, game)
    game.table.update(bob_fold, bob)

    # Charlie goes all-in for 1000
    charlie_all_in = ActionDecision(action_type=ActionType.RAISE, raise_amount=1000)
    charlie.execute(charlie_all_in, game)
    game.current_bet = 1000
    game.pot.add_to_pot(1000)
    game.table.update(charlie_all_in, charlie)

    # Alice must now either fold or call the additional 490
    call_amount = game.current_bet - alice.bet  # 1000 - 510 = 490
    alice_call = ActionDecision(action_type=ActionType.CALL, raise_amount=call_amount)
    alice.execute(alice_call, game)
    game.pot.add_to_pot(call_amount)
    game.table.update(alice_call, alice)

    # Verify correct chip counts and pot
    assert alice.chips == 0, "Alice should have called the full amount"
    assert alice.bet == 1000, "Alice's total bet should match Charlie's all-in"
    assert charlie.chips == 0, "Charlie should be all-in"
    assert charlie.bet == 1000, "Charlie's bet should be their full stack"
    assert game.pot.pot == 2000, "Pot should contain both players' full bets"


def test_all_in_player_cant_be_raised(player_factory):
    """Test that an all-in player's bet can't be raised further."""
    # Create players
    alice = player_factory(name="Alice", chips=500)  # Short stack
    bob = player_factory(name="Bob", chips=1000)
    charlie = player_factory(name="Charlie", chips=1000)

    game = AgenticPoker(players=[alice, bob, charlie])

    # Alice goes all-in for 500
    alice_all_in = ActionDecision(action_type=ActionType.RAISE, raise_amount=500)
    alice.execute(alice_all_in, game)
    game.current_bet = 500
    game.pot.add_to_pot(500)
    game.table.update(alice_all_in, alice)

    # Bob calls 500
    call_amount = game.current_bet - bob.bet  # 500 - 0 = 500
    bob_call = ActionDecision(action_type=ActionType.CALL, raise_amount=call_amount)
    bob.execute(bob_call, game)
    game.pot.add_to_pot(call_amount)
    game.table.update(bob_call, bob)

    # Charlie tries to raise to 1000
    charlie_raise = ActionDecision(action_type=ActionType.RAISE, raise_amount=1000)
    charlie.execute(charlie_raise, game)
    game.current_bet = 1000
    game.pot.add_to_pot(1000)
    game.table.update(charlie_raise, charlie)

    # Bob should only need to call 500 more to match Charlie
    call_amount = game.current_bet - bob.bet  # 1000 - 500 = 500
    bob_final_call = ActionDecision(
        action_type=ActionType.CALL, raise_amount=call_amount
    )
    bob.execute(bob_final_call, game)
    game.pot.add_to_pot(call_amount)
    game.table.update(bob_final_call, bob)

    # Verify final state
    assert alice.chips == 0, "Alice should be all-in"
    assert alice.bet == 500, "Alice's bet should be their full stack"
    assert bob.chips == 0, "Bob should have called the full raise"
    assert bob.bet == 1000, "Bob's total bet should match Charlie's"
    assert charlie.chips == 0, "Charlie should have put in the full raise"
    assert charlie.bet == 1000, "Charlie's bet should match Bob's"
    assert game.pot.pot == 2500, "Pot should contain all bets"
