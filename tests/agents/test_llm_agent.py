from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from agents.llm_agent import LLMAgent


@pytest.fixture
def mock_memory_store():
    """Create a mock memory store."""
    store = Mock()
    store.get_relevant_memories.return_value = [
        {"text": "Test memory", "metadata": {"round": 1}}
    ]
    return store


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = Mock()
    # Configure the mock with default response
    client.query.return_value = "DECISION: call\nREASONING: Test reasoning"
    return client


@pytest.fixture
def agent(mock_memory_store, mock_llm_client):
    """Create a test agent with mocked dependencies."""
    # Create agent with test configuration
    agent = LLMAgent(
        name="TestAgent",
        chips=1000,
        strategy_style="Aggressive Bluffer",
        use_reasoning=True,
        use_reflection=True,
        use_planning=True,
        use_opponent_modeling=True,
        session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
    )

    # Explicitly set mock dependencies
    agent.llm_client = mock_llm_client
    agent.memory_store = mock_memory_store

    return agent


def test_initialization(agent):
    """Test agent initialization."""
    assert agent.name == "TestAgent"
    assert agent.chips == 1000
    assert agent.strategy_style == "Aggressive Bluffer"
    assert agent.use_reasoning is True
    assert agent.use_planning is True
    assert agent.use_opponent_modeling is True
    assert hasattr(agent, "llm_client")


def test_decide_action_success(agent, mock_llm_client):
    """Test successful action decision."""
    # Set up mock response without leading newline
    test_response = "DECISION: raise 200\nREASONING: Test reasoning"

    # Mock the _query_llm method directly
    with patch.object(agent, "_query_llm", return_value=test_response) as mock_query:
        # Debug prints
        print("\nDEBUG: Starting test_decide_action_success")
        print(f"DEBUG: Test response: {repr(test_response)}")
        print(f"DEBUG: Agent's client is mock: {agent.llm_client is mock_llm_client}")

        # Debug print before action
        print("DEBUG: Calling decide_action...")

        # Add debug logging for _create_decision_prompt
        with patch.object(agent, "_create_decision_prompt") as mock_create_prompt:
            mock_create_prompt.return_value = "Test prompt"
            print("DEBUG: Mocked _create_decision_prompt")

            # Call decide_action and capture any exceptions
            try:
                action, amount = agent.decide_action("Test game state")
                print("DEBUG: decide_action completed successfully")
                print(
                    f"DEBUG: _create_decision_prompt called: {mock_create_prompt.called}"
                )
                if mock_create_prompt.called:
                    print(f"DEBUG: Prompt created: {mock_create_prompt.return_value}")
            except Exception as e:
                print(f"DEBUG: Exception in decide_action: {str(e)}")
                raise

            # Debug prints after action
            print(f"DEBUG: Received action: {action}")
            print(f"DEBUG: Received amount: {amount}")
            print(f"DEBUG: Mock _query_llm was called: {mock_query.called}")
            if mock_query.call_args:
                print(
                    f"DEBUG: Mock _query_llm called with args: {mock_query.call_args}"
                )

            # Verify the mocks were called
            assert mock_create_prompt.called, "_create_decision_prompt was not called"
            assert mock_query.called, "_query_llm was not called"

            # Verify the response was parsed correctly
            assert action == "raise", f"Expected 'raise' but got '{action}'"
            assert amount == 200, f"Expected amount 200 but got {amount}"


def test_decide_action_invalid_response(agent, mock_llm_client):
    """Test handling of invalid LLM response."""
    mock_llm_client.query.return_value = "Invalid response"

    action, amount = agent.decide_action("Test game state")

    assert action == "fold"
    assert amount == 0


def test_get_message_success(agent, mock_llm_client):
    """Test successful message generation."""
    mock_llm_client.query.return_value = "MESSAGE: Hello there!"

    message = agent.get_message("Test game state")

    assert message == "Hello there!"
    assert "TestAgent: Hello there!" in agent.table_history


def test_get_message_error(agent, mock_llm_client):
    """Test message generation error handling."""
    mock_llm_client.query.side_effect = Exception("Test error")

    message = agent.get_message("Test game state")

    assert message == ""


def test_parse_decision(agent):
    """Test decision parsing."""
    # Test valid responses
    assert agent._parse_decision("DECISION: raise 200") == "raise"
    assert agent._parse_decision("DECISION: fold") == "fold"
    assert agent._parse_decision("DECISION: call") == "call"

    # Test invalid responses
    assert agent._parse_decision("Invalid response") == "fold"
    assert agent._parse_decision("DECISION: invalid") == "fold"


def test_validate_bet_amount(agent):
    """Test bet amount validation."""
    assert agent._validate_bet_amount("raise 50") == 100  # Minimum raise
    assert agent._validate_bet_amount("raise 200") == 200
    assert agent._validate_bet_amount("call") == 0
    assert agent._validate_bet_amount("fold") == 0


def test_create_memory_query(agent):
    """Test memory query creation."""
    game_state = {
        "current_bet": 100,
        "pot": 300,
        "players": [{"name": "TestAgent", "chips": 1000, "bet": 100}],
        "position": "dealer",
    }

    query = agent._create_memory_query(game_state)

    assert "pot $300" in query
    assert "current bet $100" in query
    assert "position: dealer" in query


def test_get_relevant_memories(agent, mock_memory_store):
    """Test memory retrieval."""
    memories = agent.get_relevant_memories("test query")

    assert len(memories) == 1
    assert memories[0]["text"] == "Test memory"
    assert mock_memory_store.get_relevant_memories.called


def test_cleanup(agent):
    """Test cleanup process."""
    agent.cleanup()

    # Verify memory store was closed
    agent.memory_store.close.assert_called_once()


@pytest.mark.asyncio
async def test_async_query(agent, mock_llm_client):
    """Test async query functionality."""
    mock_llm_client.query_async.return_value = "DECISION: call"

    response = await agent._query_llm_async("Test prompt")

    assert response == "DECISION: call"
    assert mock_llm_client.query_async.called


def test_create_message_prompt(agent):
    """Test message prompt creation."""
    game_state = "Test game state"
    prompt = agent._create_message_prompt(game_state)

    # Test that key game state info is included
    assert agent.strategy_style in prompt
    assert agent.communication_style in prompt
    assert game_state in prompt

    # Test that context is included
    assert "Recent Observations:" in prompt
    assert "Relevant Memories:" in prompt
    assert "Recent Chat:" in prompt

    # Test that example responses are included
    assert "Example responses:" in prompt
    assert "Your table talk message:" in prompt


def test_parse_message(agent):
    """Test message parsing."""
    valid_response = "MESSAGE: Hello!"
    invalid_response = "Invalid response"

    assert agent._parse_message(valid_response) == "Hello!"
    assert agent._parse_message(invalid_response) == ""

    # Check table history update
    assert len(agent.table_history) > 0
    assert agent.table_history[-1] == "TestAgent: Hello!"


def test_mock_llm_setup(mock_llm_client):
    """Test that mock LLM client is set up correctly."""
    test_response = "DECISION: raise 200\nREASONING: Test reasoning"
    mock_llm_client.query.return_value = test_response

    # Debug prints
    print("\nDEBUG: Testing mock setup")
    print(f"DEBUG: Setting mock response to: {repr(test_response)}")

    result = mock_llm_client.query("test prompt")

    print(f"DEBUG: Mock returned: {repr(result)}")
    assert result == test_response, (
        f"Mock response mismatch:\n"
        f"Expected: {repr(test_response)}\n"
        f"Got: {repr(result)}"
    )
