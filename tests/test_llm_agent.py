import pytest
from unittest.mock import Mock, patch
import logging
from datetime import datetime

from agents.llm_agent import LLMAgent
from data.enums import StrategyStyle, ActionType, MessageInterpretation

@pytest.fixture
def agent():
    """Fixture to create test agent."""
    return LLMAgent(
        name="TestAgent",
        chips=1000,
        strategy_style=StrategyStyle.AGGRESSIVE,
        use_reasoning=True,
        use_reflection=True,
        use_planning=True,
        use_opponent_modeling=True
    )

def test_agent_initialization(agent):
    """Test agent initialization with various configurations."""
    assert agent.name == "TestAgent"
    assert agent.chips == 1000
    assert agent.strategy_style == StrategyStyle.AGGRESSIVE
    assert agent.use_reasoning is True
    assert agent.use_reflection is True
    assert agent.use_planning is True
    assert agent.use_opponent_modeling is True

@patch('agents.llm_agent.LLMAgent._get_llm_response')
def test_get_action(mock_llm, agent):
    """Test action generation with different cognitive mechanisms."""
    # Mock LLM response
    mock_llm.return_value = "raise 100"
    
    game_state = {
        "pot": 200,
        "current_bet": 50,
        "player_chips": 1000
    }
    
    action = agent.get_action(game_state)
    assert action == ActionType.RAISE

def test_memory_management(agent):
    """Test agent memory storage and retrieval."""
    # Store memory
    game_state = {"pot": 100}
    message = "I'm bluffing"
    
    agent.store_memory(game_state, message)
    
    # Retrieve memories
    memories = agent.get_relevant_memories("bluff")
    
    assert len(memories) > 0
    assert "bluffing" in memories[0]['text']

@patch('agents.llm_agent.LLMAgent._get_llm_response')
def test_opponent_modeling(mock_llm, agent):
    """Test opponent modeling functionality."""
    mock_llm.return_value = MessageInterpretation.COUNTER_BLUFF
    
    # Analyze opponent message
    interpretation = agent.interpret_message(
        "I have a strong hand",
        opponent_name="Opponent1"
    )
    
    assert interpretation == MessageInterpretation.COUNTER_BLUFF

def test_strategy_adaptation(agent):
    """Test strategy adaptation based on game state."""
    # Initial strategy
    initial_style = agent.strategy_style
    
    # Update game state to trigger adaptation
    agent.update_strategy({
        "chips": 100,  # Low chips
        "opponent_aggression": 0.8  # High aggression
    })
    
    # Verify strategy adapted
    assert agent.strategy_style != initial_style

def test_reasoning_chain(agent):
    """Test reasoning chain generation."""
    game_state = {
        "pot": 300,
        "hand": ["Ah", "Kh", "Qh", "Jh", "Th"],
        "opponent_bet": 100
    }
    
    reasoning = agent._generate_reasoning_chain(game_state)
    
    assert isinstance(reasoning, list)
    assert len(reasoning) > 0

def test_reflection_mechanism(agent):
    """Test reflection on past decisions."""
    # Store past decision
    agent.store_decision({
        "action": ActionType.RAISE,
        "amount": 100,
        "outcome": "lost",
        "hand": ["Ah", "Kh", "Qh", "Jh", "Th"]
    })
    
    # Generate reflection
    reflection = agent._reflect_on_past_decisions()
    
    assert isinstance(reflection, dict)
    assert "insights" in reflection

def test_planning_mechanism(agent):
    """Test strategic planning functionality."""
    game_state = {
        "chips": 1000,
        "opponent_chips": [800, 600],
        "round": 1
    }
    
    plan = agent._generate_strategic_plan(game_state)
    
    assert isinstance(plan, dict)
    assert "short_term" in plan
    assert "long_term" in plan

def test_error_handling(agent):
    """Test error handling in agent operations."""
    # Test with invalid game state
    with pytest.raises(ValueError):
        agent.get_action(None)
    
    # Test with invalid strategy style
    with pytest.raises(ValueError):
        agent.strategy_style = "Invalid Style"

def test_resource_cleanup(agent):
    """Test proper resource cleanup on agent shutdown."""
    # Use resources
    agent.store_memory({"pot": 100}, "test message")
    
    # Cleanup
    agent.cleanup()
    
    # Verify cleanup
    assert len(agent.memory_store) == 0
