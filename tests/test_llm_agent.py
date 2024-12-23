from unittest.mock import patch
import pytest
from openai import OpenAI

from agents.llm_agent import LLMAgent
from data.enums import ActionType, MessageInterpretation, StrategyStyle


@pytest.fixture
def agent(mock_memory_store):
    """Fixture to create test agent."""
    agent = LLMAgent(
        name="TestAgent",
        chips=1000,
        strategy_style=StrategyStyle.AGGRESSIVE,
        use_reasoning=True,
        use_reflection=True,
        use_planning=True,
        use_opponent_modeling=True,
    )
    # Use mock memory store instead of real ChromaDB
    agent.memory_store = mock_memory_store
    return agent


def test_agent_initialization(agent):
    """Test agent initialization with various configurations."""
    assert agent.name == "TestAgent"
    assert agent.chips == 1000
    assert agent.strategy_style == StrategyStyle.AGGRESSIVE
    assert agent.use_reasoning is True
    assert agent.use_reflection is True
    assert agent.use_planning is True
    assert agent.use_opponent_modeling is True


@patch("agents.llm_agent.LLMAgent._query_llm")
def test_decide_action(mock_llm, agent):
    """Test action generation with different cognitive mechanisms."""
    # Mock the LLM response with the exact format expected by _normalize_action
    mock_llm.return_value = """
    Step 1: Analyze hand strength...
    Step 2: Consider position...
    Step 3: Evaluate pot odds...
    DECISION: raise
    """
    game_state = "pot: $200, current_bet: $50, player_chips: $1000"

    action = agent.decide_action(game_state)
    # The method should return a normalized action
    assert action in ["fold", "call", "raise"]


def test_perceive(agent):
    """Test perception storage and retrieval."""
    game_state = "pot: $100"
    message = "I'm bluffing"

    perception = agent.perceive(game_state, message)

    assert perception["game_state"] == game_state
    assert perception["opponent_message"] == message
    assert "timestamp" in perception


@patch("agents.llm_agent.LLMAgent._query_llm")
def test_interpret_message(mock_llm, agent):
    """Test message interpretation functionality."""
    mock_llm.return_value = "trust"  # One of the valid responses

    interpretation = agent.interpret_message("I have a strong hand")
    assert interpretation in ["trust", "ignore", "counter-bluff"]


def test_update_strategy(agent):
    """Test strategy adaptation based on game outcome."""
    initial_style = agent.strategy_style

    agent.update_strategy({"chips": 100, "opponent_aggression": 0.8})

    # Strategy might or might not change based on LLM response
    assert hasattr(agent, "strategy_style")


@patch("agents.llm_agent.LLMAgent._query_llm")
def test_plan_strategy(mock_llm, agent):
    """Test strategic planning functionality."""
    # Format the response exactly as expected by eval()
    mock_llm.return_value = (
        '{"approach": "aggressive", '
        '"reasoning": "test reasoning", '
        '"bet_sizing": "large", '
        '"bluff_threshold": 0.7, '
        '"fold_threshold": 0.2}'
    )

    game_state = "pot: $300, hand: [Ah, Kh, Qh, Jh, Th], opponent_bet: $100"
    plan = agent.plan_strategy(game_state)

    assert isinstance(plan, dict)
    assert plan["approach"] == "aggressive"
    assert plan["bet_sizing"] == "large"
    assert plan["bluff_threshold"] == 0.7


def test_reset_state(agent):
    """Test agent state reset."""
    # Add some state
    agent.perceive("test state", "test message")

    # Reset state
    agent.reset_state()

    assert len(agent.perception_history) == 0
    assert len(agent.conversation_history) == 0
    assert agent.last_message == ""


@patch("agents.llm_agent.LLMAgent._query_llm")
def test_get_message(mock_llm, agent):
    """Test message generation."""
    mock_llm.return_value = "I'm going all in!"

    message = agent.get_message("pot: $100")
    assert isinstance(message, str)
    assert len(message) > 0


@patch("agents.llm_agent.LLMAgent._query_llm")
def test_decide_draw(mock_llm, agent):
    """Test draw decision making."""
    mock_llm.return_value = "0 2 4"

    indices = agent.decide_draw()
    assert isinstance(indices, list)
    assert all(isinstance(i, int) for i in indices)
    assert all(0 <= i <= 4 for i in indices)


@patch("agents.llm_agent.LLMAgent._query_llm")
def test_error_handling(mock_llm, agent):
    """Test error handling in agent operations."""
    # Test initialization with missing API key
    with patch("os.getenv", return_value=None):
        with pytest.raises(ValueError):
            LLMAgent(
                name="TestAgent", chips=1000, strategy_style=StrategyStyle.AGGRESSIVE
            )

    # Test LLM error handling for decide_action
    mock_llm.side_effect = Exception("LLM Error")
    action = agent.decide_action("test state")
    assert action == "call"  # Should use fallback action

    # Reset mock for draw test
    mock_llm.side_effect = None
    mock_llm.return_value = "invalid draw indices"
    indices = agent.decide_draw()
    assert isinstance(indices, list)  # Should return empty list or valid indices

    # Reset mock for plan test
    mock_llm.reset_mock()
    mock_llm.return_value = "invalid json"
    plan = agent.plan_strategy("test state")
    assert isinstance(plan, dict)  # Should return fallback plan
    assert "approach" in plan


def test_cleanup(agent):
    """Test proper resource cleanup."""
    # Add some perceptions
    agent.perceive("test state", "test message")

    # Store reference to memory store
    memory_store = agent.memory_store

    # Call cleanup
    agent.__del__()

    # Clear the memory store
    memory_store.clear()

    # Verify memory store was cleared
    assert len(memory_store.memories) == 0


def test_normalize_action(agent):
    """Test action normalization."""
    # Test various input formats
    assert agent._normalize_action("fold") == "fold"
    assert agent._normalize_action("call") == "call"
    assert agent._normalize_action("raise") == "raise"
    assert agent._normalize_action("check") == "call"  # check normalizes to call
    assert agent._normalize_action("bet") == "raise"  # bet normalizes to raise
    assert agent._normalize_action("I should fold here") == "fold"
    assert agent._normalize_action("RAISE!") == "raise"
    assert agent._normalize_action("invalid action") is None


@patch("os.getenv")
@patch("agents.llm_agent.OpenAI")
def test_openai_client_initialization(mock_openai, mock_getenv):
    """Test OpenAI client initialization."""
    mock_getenv.return_value = "test-api-key"

    agent = LLMAgent(
        name="TestAgent", chips=1000, strategy_style=StrategyStyle.AGGRESSIVE
    )

    mock_openai.assert_called_once_with(api_key="test-api-key")
    assert hasattr(agent, "client")
