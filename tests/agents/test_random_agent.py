import unittest
from unittest.mock import Mock, patch

from agents.random_agent import RandomAgent
from data.model import Game
from data.types.action_decision import ActionDecision, ActionType
from data.types.discard_decision import DiscardDecision


class TestRandomAgent(unittest.TestCase):
    def setUp(self):
        self.agent = RandomAgent("TestBot", chips=1000)
        self.mock_game = Mock(spec=Game)
        self.mock_game.current_bet = 100

    def test_initialization(self):
        """Test agent initialization with default and custom values."""
        agent1 = RandomAgent("Bot1")
        agent2 = RandomAgent("Bot2", chips=2000)

        self.assertEqual(agent1.name, "Bot1")
        self.assertEqual(agent1.chips, 1000)  # Default value
        self.assertEqual(agent2.name, "Bot2")
        self.assertEqual(agent2.chips, 2000)

    @patch("random.choice")
    def test_decide_action_call(self, mock_choice):
        """Test call action decision."""

        def choice_side_effect(actions):
            assert ActionType.CALL in actions, "CALL should be in available actions"
            return [a for a in actions if a == ActionType.CALL][0]

        mock_choice.side_effect = choice_side_effect

        decision = self.agent.decide_action(self.mock_game)
        self.assertEqual(decision.action_type, ActionType.CALL)
        self.assertIsNone(decision.raise_amount)

    @patch("random.choice")
    @patch("random.randrange")
    def test_decide_action_raise(self, mock_randrange, mock_choice):
        """Test raise action decision."""

        def choice_side_effect(actions):
            assert ActionType.RAISE in actions, "RAISE should be in available actions"
            return [a for a in actions if a == ActionType.RAISE][0]

        mock_choice.side_effect = choice_side_effect
        mock_randrange.return_value = 250

        decision = self.agent.decide_action(self.mock_game)

        self.assertEqual(decision.action_type, ActionType.RAISE)
        self.assertEqual(decision.raise_amount, 250)

    def test_decide_action_insufficient_chips(self):
        """Test behavior when agent can't afford current bet."""
        self.agent.chips = 50  # Set chips lower than current bet
        decision = self.agent.decide_action(self.mock_game)

        self.assertEqual(decision.action_type, ActionType.FOLD)

    def test_decide_action_error_handling(self):
        """Test error handling in decide_action."""
        self.mock_game.current_bet = "invalid"  # This will cause an error
        decision = self.agent.decide_action(self.mock_game)

        self.assertEqual(decision.action_type, ActionType.FOLD)

    @patch("random.randint")
    @patch("random.sample")
    def test_decide_discard_no_cards(self, mock_sample, mock_randint):
        """Test discard decision with no cards."""
        mock_randint.return_value = 0
        decision = self.agent.decide_discard()

        self.assertEqual(decision.discard, [])
        mock_sample.assert_not_called()

    @patch("random.randint")
    @patch("random.sample")
    def test_decide_discard_with_cards(self, mock_sample, mock_randint):
        """Test discard decision with cards."""
        mock_randint.return_value = 2
        mock_sample.return_value = [1, 3]

        decision = self.agent.decide_discard()

        self.assertEqual(decision.discard, [1, 3])
        mock_sample.assert_called_once_with(list(range(5)), 2)

    def test_get_message(self):
        """Test that get_message returns empty string."""
        message = self.agent.get_message("any_state")
        self.assertEqual(message, "")

    @patch("random.randint")
    @patch("random.sample")
    def test_decide_draw(self, mock_sample, mock_randint):
        """Test draw decision."""
        mock_randint.return_value = 2
        mock_sample.return_value = [0, 4]

        decision = self.agent.decide_draw()

        self.assertEqual(decision, [0, 4])
        mock_sample.assert_called_once_with(list(range(5)), 2)

    def test_perceive(self):
        """Test that perceive returns empty dict."""
        result = self.agent.perceive("state", "message")
        self.assertEqual(result, {})

    def test_update_from_reward(self):
        """Test that update_from_reward doesn't raise exceptions."""
        try:
            self.agent.update_from_reward(100, {"state": "data"})
        except Exception as e:
            self.fail(f"update_from_reward raised an exception: {e}")

    @patch("random.choice")
    def test_decide_action_available_actions(self, mock_choice):
        """Test that the correct actions are available for choice."""

        def choice_side_effect(actions):
            assert len(actions) >= 2, "Should have at least FOLD and CALL available"
            return ActionType.FOLD

        mock_choice.side_effect = choice_side_effect

        self.agent.decide_action(self.mock_game)

        # Verify that random.choice was called with the correct available actions
        called_actions = mock_choice.call_args[0][0]
        expected_actions = [ActionType.FOLD, ActionType.CALL, ActionType.RAISE]
        self.assertEqual(set(called_actions), set(expected_actions))

    @patch("random.choice")
    def test_decide_action_minimum_raise(self, mock_choice):
        """Test that raise falls back to call when only minimum raise is possible."""
        mock_choice.side_effect = lambda x: ActionType.RAISE
        print("\nDebug test_decide_action_minimum_raise:")
        print(f"Initial chips: {self.agent.chips}")
        print(f"Current bet: {self.mock_game.current_bet}")

        # Set chips to exactly match minimum raise (2x current bet)
        self.agent.chips = 200  # Current bet is 100, so minimum raise would be 200
        self.mock_game.current_bet = 100

        print(
            f"After setup - chips: {self.agent.chips}, current bet: {self.mock_game.current_bet}"
        )

        decision = self.agent.decide_action(self.mock_game)

        print(f"Mock was called {mock_choice.call_count} times")
        if mock_choice.call_args:
            print(f"Mock was called with args: {mock_choice.call_args}")
        print(f"Decision returned: {decision}")
        print(f"Decision action type: {decision.action_type}")

        # Should fall back to call since minimum raise would equal all chips
        self.assertEqual(decision.action_type, ActionType.CALL)


if __name__ == "__main__":
    unittest.main()
