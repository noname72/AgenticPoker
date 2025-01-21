from unittest.mock import Mock, patch

import pytest

from agents.agent import Agent
from data.types.action_decision import ActionDecision, ActionType
from game.evaluator import HandEvaluation


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = Mock()
    client.query.return_value = "DECISION: call"
    return client


@pytest.fixture
def basic_agent(mock_llm_client):
    """Create a basic agent for testing."""
    with patch("agents.agent.LLMClient", return_value=mock_llm_client), patch(
        "agents.agent.ChromaMemoryStore"
    ) as mock_memory:
        # Setup mock memory store
        mock_store = mock_memory.return_value
        mock_store.get_relevant_memories.return_value = []
        mock_store.add_memory.return_value = None

        agent = Agent(
            name="TestAgent",
            chips=1000,
            strategy_style="Aggressive Bluffer",
            use_reasoning=True,
            use_reflection=True,
            use_planning=True,
            session_id="test_session",
        )
        # Mock memory-related methods
        agent.get_relevant_memories = mock_store.get_relevant_memories
        agent._create_memory_query = Mock(return_value="test query")
        return agent


class TestAgent:
    def test_initialization(self, basic_agent):
        """Test agent initialization."""
        assert basic_agent.name == "TestAgent"
        assert basic_agent.chips == 1000
        assert basic_agent.strategy_style == "Aggressive Bluffer"
        assert basic_agent.use_reasoning is True
        assert basic_agent.use_reflection is True
        assert basic_agent.use_planning is True
        assert basic_agent.communication_style == "Intimidating"
        assert basic_agent.emotional_state == "confident"
        assert isinstance(basic_agent.personality_traits, dict)

    def test_basic_decision(self, basic_agent, mock_llm_client):
        """Test basic decision making."""
        mock_game = Mock()
        mock_game.get_state.return_value = "Current game state"
        mock_hand_eval = Mock(spec=HandEvaluation)
        mock_hand_eval.rank = 5
        mock_hand_eval.description = "Flush"
        mock_hand_eval.tiebreakers = [14, 13, 12, 11, 10]

        # Test call decision
        mock_llm_client.query.return_value = "DECISION: call"
        response = basic_agent._basic_decision(mock_game, mock_hand_eval)
        assert isinstance(response, ActionDecision)
        assert response.action_type == ActionType.CALL
        assert response.raise_amount is None

        # Test raise decision
        mock_llm_client.query.return_value = "DECISION: raise 100"
        response = basic_agent._basic_decision(mock_game, mock_hand_eval)
        assert response.action_type == ActionType.RAISE
        assert response.raise_amount == 100

        # Test fold decision
        mock_llm_client.query.return_value = "DECISION: fold"
        response = basic_agent._basic_decision(mock_game, mock_hand_eval)
        assert response.action_type == ActionType.FOLD
        assert response.raise_amount is None

    # @patch("game.player.Player.perceive")
    # def test_perceive(self, mock_perceive, basic_agent):
    #     """Test perception functionality."""
    #     game_state = "Current game state"
    #     opponent_message = "I raise"
    #     mock_perceive.return_value = {"timestamp": 123, "game_state": game_state}

    #     perception = basic_agent.perceive(game_state, opponent_message)

    #     assert perception is not None
    #     assert len(basic_agent.perception_history) > 0
    #     assert opponent_message in basic_agent.table_history
    #     assert len(basic_agent.table_history) <= 10  # Check history limit

    # @patch("agents.agent.StrategyPlanner")
    # def test_analyze_opponent(self, mock_planner, basic_agent):
    #     """Test opponent analysis."""
    #     opponent_name = "Opponent1"
    #     game_state = "Current game state"

    #     analysis = basic_agent.analyze_opponent(opponent_name, game_state)

    #     assert isinstance(analysis, dict)
    #     assert "patterns" in analysis
    #     assert "threat_level" in analysis
    #     assert "style" in analysis
    #     assert "weaknesses" in analysis
    #     assert "strengths" in analysis
    #     assert "recommended_adjustments" in analysis

    def test_get_message(self, basic_agent, mock_llm_client):
        """Test message generation."""
        mock_game = Mock()
        mock_game.get_state.return_value = "Current game state"

        mock_llm_client.query.return_value = "I'm feeling lucky!"
        message = basic_agent.get_message(mock_game)

        assert isinstance(message, str)
        assert len(message) > 0

    def test_cleanup(self, basic_agent):
        """Test cleanup functionality."""
        # Add some data to clean up
        basic_agent.perception_history = ["perception1", "perception2"]
        basic_agent.conversation_history = ["conv1", "conv2"]
        basic_agent.opponent_stats = {"player1": {"actions": {}}}

        basic_agent.close()

        assert not hasattr(basic_agent, "perception_history")
        assert not hasattr(basic_agent, "conversation_history")
        assert not hasattr(basic_agent, "opponent_stats")

    def test_error_handling(self, basic_agent, mock_llm_client):
        """Test error handling in decision making."""
        mock_game = Mock()
        mock_game.get_state.return_value = "Current game state"
        mock_hand_eval = Mock(spec=HandEvaluation)
        mock_hand_eval.rank = 5
        mock_hand_eval.description = "Flush"
        mock_hand_eval.tiebreakers = [14, 13, 12, 11, 10]

        # Test invalid LLM response
        mock_llm_client.query.return_value = "INVALID RESPONSE"
        response = basic_agent._basic_decision(mock_game, mock_hand_eval)
        assert response.action_type == ActionType.FOLD
        assert response.raise_amount is None

        # Test LLM error
        mock_llm_client.query.side_effect = Exception("LLM Error")
        response = basic_agent._basic_decision(mock_game, mock_hand_eval)
        assert response.action_type == ActionType.FOLD
        assert response.raise_amount is None
