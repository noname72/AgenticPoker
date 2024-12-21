import unittest
from unittest.mock import Mock, patch
import logging

from poker_agents import (
    PokerAgent,
    LLMError,
    OpenAIError,
    LocalLLMError,
    ActionType,
    StrategyStyle,
)

class TestPokerAgent(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Disable logging during tests
        logging.disable(logging.CRITICAL)
        
        self.agent = PokerAgent(
            name="TestAgent",
            model_type="gpt",
            strategy_style=StrategyStyle.AGGRESSIVE.value
        )
        
        # Mock the OpenAI client
        self.mock_client = Mock()
        self.agent.client = self.mock_client

    def tearDown(self):
        """Clean up after each test method."""
        logging.disable(logging.NOTSET)

    def test_normalize_action_valid(self):
        """Test action normalization with valid inputs."""
        test_cases = [
            ("fold", "fold"),
            ("FOLD", "fold"),
            ("I will fold", "fold"),
            ("check", "call"),
            ("bet", "raise"),
            ("**Decision: Raise**", "raise"),
            ("'call'", "call"),
            ('"raise"', "raise"),
        ]
        
        for input_action, expected in test_cases:
            with self.subTest(input_action=input_action):
                result = self.agent._normalize_action(input_action)
                self.assertEqual(result, expected)

    def test_normalize_action_invalid(self):
        """Test action normalization with invalid inputs."""
        invalid_actions = [
            "invalid",
            "thinking...",
            "",
            "maybe fold?",
            "all-in",
        ]
        
        for action in invalid_actions:
            with self.subTest(action=action):
                result = self.agent._normalize_action(action)
                self.assertIsNone(result)

    @patch('poker_agents.OpenAI')
    def test_get_action_success(self, mock_openai):
        """Test successful action retrieval."""
        # Mock the LLM response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="raise"))]
        self.mock_client.chat.completions.create.return_value = mock_response

        game_state = {"pot": 100, "players": 2}
        action = self.agent.get_action(game_state)
        
        self.assertEqual(action, "raise")
        self.mock_client.chat.completions.create.assert_called_once()

    @patch('poker_agents.OpenAI')
    def test_get_action_llm_error(self, mock_openai):
        """Test action retrieval with LLM error."""
        # Mock an API error
        self.mock_client.chat.completions.create.side_effect = Exception("API Error")

        game_state = {"pot": 100, "players": 2}
        action = self.agent.get_action(game_state)
        
        # Should fall back to fold on error
        self.assertEqual(action, "fold")

    def test_interpret_message(self):
        """Test message interpretation."""
        # Mock the LLM response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="counter-bluff"))]
        self.mock_client.chat.completions.create.return_value = mock_response

        interpretation = self.agent.interpret_message("I have a strong hand")
        self.assertEqual(interpretation, "counter-bluff")

    def test_strategy_style_validation(self):
        """Test strategy style validation."""
        # Valid strategy styles
        for style in StrategyStyle:
            with self.subTest(style=style.value):
                agent = PokerAgent("TestAgent", strategy_style=style.value)
                self.assertEqual(agent.strategy_style, style.value)

        # Invalid strategy style should use random valid style
        agent = PokerAgent("TestAgent", strategy_style="Invalid Style")
        self.assertIn(agent.strategy_style, [s.value for s in StrategyStyle])

    def test_perception_history(self):
        """Test perception history management."""
        game_state = {"pot": 100}
        opponent_message = "I'm bluffing"
        
        perception = self.agent.perceive(game_state, opponent_message)
        
        self.assertEqual(len(self.agent.perception_history), 1)
        self.assertEqual(perception["game_state"], game_state)
        self.assertEqual(perception["opponent_message"], opponent_message)
        self.assertIn("timestamp", perception)

    def test_reset_state(self):
        """Test agent state reset."""
        # Add some history
        self.agent.perceive({"pot": 100}, "message")
        self.agent.last_message = "old message"
        
        # Reset state
        self.agent.reset_state()
        
        self.assertEqual(len(self.agent.perception_history), 0)
        self.assertEqual(self.agent.last_message, "")

if __name__ == '__main__':
    unittest.main() 