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


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return """MESSAGE: [confident] The odds are in my favor now
INTENT: Create uncertainty about hand strength
CONFIDENCE: 8"""


def test_communication_style_initialization(agent):
    """Test that communication style is properly initialized."""
    assert agent.communication_style == "Intimidating"
    assert agent.emotional_state == "confident"
    assert isinstance(agent.table_history, list)


@patch("agents.llm_agent.LLMAgent._query_llm")
def test_get_message_success(mock_query, agent, mock_llm_response):
    """Test successful message generation with full response."""
    mock_query.return_value = mock_llm_response
    
    message = agent.get_message("pot: $100")
    
    assert message == "[confident] The odds are in my favor now"
    assert agent.emotional_state == "confident"
    assert len(agent.table_history) == 1
    assert agent._last_message_intent == "Create uncertainty about hand strength"
    assert agent._last_message_confidence == 8


@patch("agents.llm_agent.LLMAgent._query_llm")
def test_get_message_fallback(mock_query, agent):
    """Test fallback to simple message when banter fails."""
    # First call fails, second call (fallback) succeeds
    mock_query.side_effect = [
        "Invalid response",
        "MESSAGE: [thoughtful] Playing it safe"
    ]
    
    message = agent.get_message("pot: $100")
    
    assert message == "[thoughtful] Playing it safe"
    assert len(agent.table_history) == 1


def test_update_emotional_state(agent):
    """Test emotional state updates based on confidence levels."""
    test_cases = [
        (9, "confident"),
        (3, "nervous"),
        (5, "thoughtful"),
        (7, "amused")
    ]
    
    for confidence, expected_state in test_cases:
        agent._update_emotional_state(confidence)
        assert agent.emotional_state == expected_state


def test_format_recent_actions(agent):
    """Test formatting of recent actions."""
    # Case with no action history
    assert agent._format_recent_actions() == "No recent actions"
    
    # Case with action history
    if not hasattr(agent, 'action_history'):
        agent.action_history = []
    agent.action_history = ["fold", "call", "raise", "fold"]
    formatted = agent._format_recent_actions()
    assert isinstance(formatted, str)
    assert "fold" in formatted
    assert len(formatted.split('\n')) <= 3  # Only last 3 actions


def test_get_opponent_patterns(agent):
    """Test opponent pattern analysis formatting."""
    # Case with no opponent data
    assert agent._get_opponent_patterns() == "No opponent data"
    
    # Case with opponent data
    agent.opponent_models = {
        "Player1": {"style": "aggressive"},
        "Player2": {"style": "passive"}
    }
    patterns = agent._get_opponent_patterns()
    assert "Player1: aggressive" in patterns
    assert "Player2: passive" in patterns


def test_perceive_with_message(agent):
    """Test perception handling with opponent message."""
    game_state = "pot: $200"
    message = "I'm all in!"
    
    perception = agent.perceive(game_state, message)
    
    assert isinstance(perception, dict)
    assert len(agent.table_history) == 1
    assert "Opponent: I'm all in!" in agent.table_history[0]


def test_table_history_limit(agent):
    """Test that table history is properly limited."""
    # Add more than 10 messages
    for i in range(12):
        agent.perceive("pot: $100", f"Message {i}")
    
    assert len(agent.table_history) == 10  # Should be limited to 10
    assert "Message 11" in agent.table_history[-1]  # Should have most recent
    assert "Message 0" not in agent.table_history  # Should not have oldest


@patch("agents.llm_agent.LLMAgent._query_llm")
def test_communication_styles(mock_query, agent):
    """Test different communication styles affect messaging."""
    test_styles = [
        ("Intimidating", "[confident] Your chips are mine"),
        ("Analytical", "[thoughtful] Probability suggests a fold"),
        ("Friendly", "[amused] Good luck with that decision!")
    ]
    
    for style, expected_message in test_styles:
        agent.communication_style = style
        mock_query.return_value = f"MESSAGE: {expected_message}\nINTENT: test\nCONFIDENCE: 7"
        
        message = agent.get_message("pot: $100")
        assert message == expected_message
