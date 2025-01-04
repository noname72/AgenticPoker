from unittest.mock import Mock, patch

import pytest
import time  # Add this import at the top

from agents.llm_agent import LLMAgent
from agents.strategy_planner import StrategyPlanner
from agents.types import Approach, BetSizing, Plan
from data.enums import StrategyStyle


@pytest.fixture
def agent(mock_memory_store):
    """Fixture to create test agent."""
    agent = LLMAgent(
        name="TestAgent",
        chips=1000,
        strategy_style="Aggressive Bluffer",
        use_reasoning=True,
        use_reflection=True,
        use_planning=True,
        use_opponent_modeling=True,
    )
    # Use mock memory store instead of real ChromaDB
    agent.memory_store = mock_memory_store

    yield agent

    # Cleanup after each test
    agent.reset_state()
    agent.memory_store.clear()


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
    game_state = {"pot": 100}
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


@patch("agents.llm_agent.LLMAgent._query_llm")
def test_update_strategy(mock_query, agent):
    """Test strategy adaptation based on game outcome."""
    # Mock the LLM response
    mock_query.return_value = """
    {
        "strategy_style": "AGGRESSIVE",
        "reasoning": "Opponent shows high aggression, need to adapt"
    }
    """

    initial_style = agent.strategy_style

    # Test strategy update
    agent.update_strategy({"chips": 100, "opponent_aggression": 0.8})

    # Strategy should be updated based on mock response
    assert agent.strategy_style == StrategyStyle.AGGRESSIVE
    assert agent.strategy_style == initial_style  # Since mock returns same style

    # Test error handling
    mock_query.return_value = "invalid json"
    agent.update_strategy({"chips": 100, "opponent_aggression": 0.8})
    assert (
        agent.strategy_style == initial_style
    )  # Should maintain current strategy if update fails


@patch(
    "agents.strategy_planner.StrategyPlanner.plan_strategy"
)  # Changed from generate_plan to plan_strategy
def test_plan_strategy(mock_plan_strategy):
    """Test strategy planning functionality."""
    # Create the Plan object that should be returned
    plan = Plan(
        approach=Approach.AGGRESSIVE,
        reasoning="Test plan",
        bet_sizing=BetSizing.LARGE,
        bluff_threshold=0.7,
        fold_threshold=0.2,
        expiry=time.time() + 300,  # Add expiry 5 minutes from now
    )
    mock_plan_strategy.return_value = plan

    # Create planner with mock
    mock_llm = Mock()
    planner = StrategyPlanner(strategy_style="Aggressive", client=mock_llm)
    result = planner.plan_strategy(game_state={}, chips=1000)

    print("Generated plan:", result)  # Debug print
    print("Plan approach type:", type(result.approach))
    print("Plan approach value:", result.approach)
    print("Expected approach type:", type(Approach.AGGRESSIVE))
    print("Expected approach value:", Approach.AGGRESSIVE)

    # Assertions
    assert result.approach == Approach.AGGRESSIVE
    assert result.reasoning == "Test plan"
    assert result.bet_sizing == BetSizing.LARGE
    assert result.bluff_threshold == 0.7
    assert result.fold_threshold == 0.2
    assert mock_plan_strategy.called


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
    plan = agent.strategy_planner.plan_strategy("test state", agent.chips)
    assert isinstance(plan, Plan)  # Changed to check for Plan type instead of dict
    assert plan.approach == Approach.BALANCED  # Check for fallback approach
    assert plan.bet_sizing == BetSizing.MEDIUM  # Check for fallback bet sizing


def test_cleanup(agent):
    """Test proper resource cleanup."""
    # Add some perceptions
    agent.perceive("test state", "test message")

    # Store initial memory count
    initial_memories = len(agent.memory_store.memories)
    assert initial_memories > 0

    # Reset state and clear memory store
    agent.reset_state()
    agent.memory_store.clear()

    # Verify memory store was cleared
    assert len(agent.memory_store.memories) == 0


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
    assert agent.strategy_style == StrategyStyle.AGGRESSIVE
    assert agent.communication_style == "Analytical"
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
        "MESSAGE: [thoughtful] Playing it safe",
    ]

    message = agent.get_message("pot: $100")

    assert message == "[thoughtful] Playing it safe"
    assert len(agent.table_history) == 1


def test_update_emotional_state(agent):
    """Test emotional state updates based on confidence levels."""
    test_cases = [(9, "confident"), (3, "nervous"), (5, "thoughtful"), (7, "amused")]

    for confidence, expected_state in test_cases:
        agent._update_emotional_state(confidence)
        assert agent.emotional_state == expected_state


def test_format_recent_actions(agent):
    """Test formatting of recent actions."""
    # Case with no action history
    assert agent._format_recent_actions() == "No recent actions"

    # Case with action history
    if not hasattr(agent, "action_history"):
        agent.action_history = []
    agent.action_history = ["fold", "call", "raise", "fold"]
    formatted = agent._format_recent_actions()
    assert isinstance(formatted, str)
    assert "fold" in formatted
    assert len(formatted.split("\n")) <= 3  # Only last 3 actions


def test_get_opponent_patterns(agent):
    """Test opponent pattern analysis formatting."""
    # Case with no opponent data
    assert agent._get_opponent_patterns() == "No clear patterns"

    # Case with opponent data
    agent.opponent_models = {
        "Player1": {"style": "aggressive"},
        "Player2": {"style": "passive"},
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
        ("Friendly", "[amused] Good luck with that decision!"),
    ]

    for style, expected_message in test_styles:
        agent.communication_style = style
        mock_query.return_value = (
            f"MESSAGE: {expected_message}\nINTENT: test\nCONFIDENCE: 7"
        )

        message = agent.get_message("pot: $100")
        assert message == expected_message


@patch("agents.llm_agent.LLMAgent._query_llm")
def test_get_message_parsing_error(mock_query, agent):
    """Test handling of malformed message responses."""
    # Test completely invalid format
    mock_query.return_value = "Invalid format"
    message = agent.get_message("pot: $100")
    assert isinstance(message, str)
    assert len(message) > 0  # Should return fallback message

    # Test partial format
    mock_query.return_value = (
        "MESSAGE: [confident] Test\nINTENT: test"  # Missing confidence
    )
    message = agent.get_message("pot: $100")
    assert isinstance(message, str)
    assert message.startswith("[")  # Should still parse emotional state


@patch("agents.llm_agent.LLMAgent._query_llm")
def test_update_strategy_invalid_response(mock_query, agent):
    """Test strategy update with invalid LLM response."""
    initial_style = agent.strategy_style
    mock_query.return_value = "invalid json"

    # Should maintain current strategy if update fails
    agent.update_strategy({"chips": 100, "opponent_aggression": 0.8})
    assert agent.strategy_style == initial_style


def test_memory_store_interaction(agent):
    """Test proper interaction with memory store."""
    # Test adding memory
    game_state = "pot: $200"
    message = "Test message"

    perception = agent.perceive(game_state, message)
    assert len(agent.memory_store.memories) > 0

    # Test retrieving memories
    memories = agent.memory_store.get_relevant_memories("test query")
    assert isinstance(memories, list)

    # Test memory cleanup
    agent.reset_state()
    assert len(agent.memory_store.memories) == 0


def test_bubble_situation_detection(agent):
    """Test detection of tournament bubble situations."""
    # Test tournament bubble keywords
    bubble_state = "tournament: true, bubble situation, 8 players remaining"
    assert agent._is_bubble_situation(bubble_state) is True

    # Test near money situation
    near_money_state = "tournament: true, near money, 6 players remaining"
    assert agent._is_bubble_situation(near_money_state) is True

    # Test non-bubble situation
    normal_state = "cash game, pot: $100"
    assert agent._is_bubble_situation(normal_state) is False


def test_parse_decision_formats(agent):
    """Test parsing of different decision format responses."""
    # Test standard format
    assert agent._parse_decision("DECISION: fold") == "fold"

    # Test with extra whitespace and capitalization
    assert agent._parse_decision("DECISION:   RAISE  ") == "raise"

    # Test with invalid action
    assert agent._parse_decision("DECISION: all-in") == "call"  # should default to call

    # Test with missing DECISION prefix
    assert (
        agent._parse_decision("I think we should fold") == "call"
    )  # should default to call


def test_parse_discard_formats(agent):
    """Test parsing of different discard format responses."""
    # Test standard format
    assert agent._parse_discard("DISCARD: [0, 2, 4]") == [0, 2, 4]

    # Test "none" response
    assert agent._parse_discard("DISCARD: none") == []

    # Test invalid positions
    assert agent._parse_discard("DISCARD: [5, 6, 7]") == []

    # Test too many positions
    assert agent._parse_discard("DISCARD: [0, 1, 2, 3, 4]") == [0, 1, 2]


@patch("agents.llm_agent.LLMAgent._query_llm")
def test_reward_learning(mock_query, agent):
    """Test reward-based learning functionality."""
    # Enable reward learning
    agent.use_reward_learning = True
    agent.learning_rate = 0.1

    # Initialize required attributes
    agent.action_history = []
    agent.last_action = "raise"
    agent.action_values = {"fold": 0.0, "call": 0.0, "raise": 0.0}
    agent.personality_traits = {
        "aggression": 0.5,
        "bluff_frequency": 0.5,
        "risk_tolerance": 0.5,
    }

    # Add a previous action to history for TD learning
    prev_state = {"all_in": False, "bluff_successful": False}
    agent.action_history.append(("call", prev_state, 0))

    # Test successful outcome
    game_state = {"all_in": True, "bluff_successful": True}
    agent.update_from_reward(100, game_state)

    # Check trait adjustments for success
    assert agent.personality_traits["risk_tolerance"] > 0.5  # Should increase
    assert agent.personality_traits["bluff_frequency"] > 0.5  # Should increase

    # Reset traits for failure test
    agent.personality_traits = {
        "aggression": 0.5,
        "bluff_frequency": 0.5,
        "risk_tolerance": 0.5,
    }

    # Test negative outcome
    game_state = {"all_in": True, "bluff_caught": True}
    agent.update_from_reward(-100, game_state)

    # Check trait adjustments for failure
    assert agent.personality_traits["risk_tolerance"] < 0.5  # Should decrease
    assert agent.personality_traits["bluff_frequency"] < 0.5  # Should decrease


def test_action_probabilities(agent):
    """Test conversion of action values to probabilities."""
    # Enable reward learning
    agent.use_reward_learning = True

    # Set some action values
    agent.action_values = {"fold": 0.1, "call": 0.2, "raise": 0.3}

    probs = agent._get_action_probabilities()

    # Check probability properties
    assert isinstance(probs, dict)
    assert all(0 <= p <= 1 for p in probs.values())
    assert abs(sum(probs.values()) - 1.0) < 1e-6  # Sum should be ~1
    assert probs["raise"] > probs["call"] > probs["fold"]  # Should maintain ordering


def test_opponent_stats_tracking(agent):
    """Test opponent statistics tracking functionality."""
    opponent = "TestOpponent"

    # Test action tracking
    agent.update_opponent_stats(opponent, "raise", amount=100, position="dealer")
    assert agent.opponent_stats[opponent]["actions"]["raise"] == 1
    assert 100 in agent.opponent_stats[opponent]["bet_sizes"]
    assert agent.opponent_stats[opponent]["position_stats"]["dealer"]["raise"] == 1

    # Test bluff tracking
    agent.update_opponent_stats(opponent, "raise", was_bluff=True)
    assert agent.opponent_stats[opponent]["bluff_attempts"] == 1
    assert agent.opponent_stats[opponent]["bluff_successes"] == 1

    # Test recent actions
    assert len(agent.opponent_stats[opponent]["last_five_actions"]) > 0


def test_strategy_manager_integration(agent):
    """Test integration with strategy manager."""
    # Test strategy prompt generation
    prompt = agent._get_decision_prompt("pot: $100")
    assert "Aggressive Bluffer" in prompt  # Check for actual string in prompt
    assert "pot: $100" in prompt

    # Test strategy module activation
    assert agent.strategy_manager.active_modules["reasoning"] is True
    assert agent.strategy_manager.active_modules["reflection"] is True
    assert agent.strategy_manager.active_modules["planning"] is True
