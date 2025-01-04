import unittest
from unittest.mock import patch, MagicMock
from agents.base_agent import BaseAgent


class TestBaseAgent(unittest.TestCase):
    def setUp(self):
        self.agent = BaseAgent("TestAgent", chips=1000)

    def test_initialization(self):
        """Test agent initialization"""
        self.assertEqual(self.agent.name, "TestAgent")
        self.assertEqual(self.agent.chips, 1000)
        self.assertIsNotNone(self.agent.logger)

    def test_decide_action_with_sufficient_chips(self):
        """Test decide_action when agent has enough chips to call"""
        game_state = {"current_bet": 500, "pot": 1000}
        action = self.agent.decide_action(game_state)
        self.assertEqual(action, "call")

    def test_decide_action_with_insufficient_chips(self):
        """Test decide_action when agent doesn't have enough chips to call"""
        game_state = {"current_bet": 1500, "pot": 1000}  # More than agent's chips
        action = self.agent.decide_action(game_state)
        self.assertEqual(action, "fold")

    def test_decide_action_with_string_game_state(self):
        """Test decide_action with legacy string game state"""
        action = self.agent.decide_action("some string game state")
        self.assertEqual(action, "call")

    def test_decide_action_with_error(self):
        """Test decide_action error handling"""
        game_state = None
        action = self.agent.decide_action(game_state)
        self.assertEqual(action, "fold")

    def test_get_message(self):
        """Test get_message returns empty string"""
        game_state = {"pot": 1000}
        message = self.agent.get_message(game_state)
        self.assertEqual(message, "")

    def test_decide_draw(self):
        """Test decide_draw returns empty list"""
        draw_decision = self.agent.decide_draw()
        self.assertEqual(draw_decision, [])

    def test_perceive_with_dict_game_state(self):
        """Test perceive with dictionary game state"""
        game_state = {"current_bet": 100, "pot": 200}
        opponent_message = "Hello"

        perception = self.agent.perceive(game_state, opponent_message)

        self.assertEqual(perception["game_state"], game_state)
        self.assertEqual(perception["opponent_message"], opponent_message)
        self.assertIn("timestamp", perception)

    def test_perceive_with_string_game_state(self):
        """Test perceive with string game state"""
        game_state = "string game state"
        perception = self.agent.perceive(game_state)

        self.assertEqual(perception["game_state"]["raw"], "string game state")
        self.assertIsNone(perception["opponent_message"])
        self.assertIn("timestamp", perception)

    def test_perceive_with_error(self):
        """Test perceive error handling"""
        game_state = None
        perception = self.agent.perceive(game_state)

        self.assertEqual(perception["game_state"], {})
        self.assertIsNone(perception["opponent_message"])
        self.assertIn("timestamp", perception)
        self.assertIn("error", perception)

    @patch("logging.getLogger")
    def test_logging(self, mock_get_logger):
        """Test that errors are properly logged"""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Create agent with mocked logger
        agent = BaseAgent("TestAgent")
        agent.logger = mock_logger  # Explicitly set the mocked logger

        # Trigger an error
        agent.decide_action(None)

        # Verify error was logged
        mock_logger.error.assert_called_once_with("Received None game state")


if __name__ == "__main__":
    unittest.main()
