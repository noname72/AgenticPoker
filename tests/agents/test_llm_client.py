import time
from unittest.mock import Mock, patch

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from agents.llm_client import LLMClient
from exceptions import LLMError


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = Mock()

    # Create a mock response structure matching OpenAI's response format
    mock_response = ChatCompletion(
        id="test_id",
        model="gpt-3.5-turbo",
        object="chat.completion",
        created=1234567890,
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=ChatCompletionMessage(
                    content="Test response",
                    role="assistant",
                ),
            )
        ],
        usage={"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50},
    )

    client.chat.completions.create.return_value = mock_response
    return client


@pytest.fixture
def llm_client(mock_openai_client):
    """Create an LLMClient instance with a mock OpenAI client."""
    return LLMClient(
        api_key="test-key", 
        client=mock_openai_client,
        max_retries=5  # Update to match new default in LLMClient
    )


def test_initialization(llm_client):
    """Test LLMClient initialization."""
    assert llm_client.model == "gpt-3.5-turbo"
    assert llm_client.max_retries == 5
    assert llm_client.base_wait == 1.0
    assert llm_client.max_wait == 10.0
    assert llm_client.metrics["total_queries"] == 0


def test_query_success(llm_client, mock_openai_client):
    """Test successful query execution."""
    response = llm_client.query("Test prompt")

    assert response == "Test response"
    assert llm_client.metrics["total_queries"] == 1
    assert len(llm_client.metrics["query_times"]) == 1
    assert llm_client.metrics["total_tokens"] == 100


def test_query_with_system_message(llm_client, mock_openai_client):
    """Test query with system message."""
    llm_client.query("Test prompt", system_message="System context")

    # Verify correct message structure was sent
    call_args = mock_openai_client.chat.completions.create.call_args[1]
    messages = call_args["messages"]

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "System context"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Test prompt"


@patch("time.sleep", return_value=None)
def test_query_all_retries_fail(mock_sleep, llm_client, mock_openai_client):
    """Test when all retry attempts fail."""
    # Make all calls fail
    mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

    with pytest.raises(LLMError):
        llm_client.query("Test prompt")

    # Verify metrics
    assert (
        llm_client.metrics["failed_queries"] == 5
    )  # Each retry counts as a failed query (5 attempts total)
    assert llm_client.metrics["retry_count"] == 5  # Five retry attempts
    assert mock_openai_client.chat.completions.create.call_count == 5


@pytest.mark.asyncio
async def test_query_async(llm_client, mock_openai_client):
    """Test asynchronous query execution."""
    response = await llm_client.query_async("Test prompt")

    assert response == "Test response"
    assert llm_client.metrics["total_queries"] == 1


def test_metrics_tracking(llm_client):
    """Test metrics tracking functionality."""
    # Execute some queries
    llm_client.query("Test 1")
    llm_client.query("Test 2")

    metrics = llm_client.get_metrics()

    assert metrics["total_queries"] == 2
    assert len(metrics["query_times"]) == 2
    assert "average_query_time" in metrics
    assert metrics["total_tokens"] == 200  # 100 per query


def test_reset_metrics(llm_client):
    """Test metrics reset functionality."""
    # Execute a query to generate metrics
    llm_client.query("Test")

    # Reset metrics
    llm_client.reset_metrics()

    assert llm_client.metrics["total_queries"] == 0
    assert len(llm_client.metrics["query_times"]) == 0
    assert llm_client.metrics["total_tokens"] == 0


def test_temperature_setting(llm_client, mock_openai_client):
    """Test temperature parameter is correctly passed."""
    llm_client.query("Test", temperature=0.5)

    call_args = mock_openai_client.chat.completions.create.call_args[1]
    assert call_args["temperature"] == 0.5


def test_max_tokens_setting(llm_client, mock_openai_client):
    """Test max_tokens parameter is correctly passed."""
    llm_client.query("Test", max_tokens=100)

    call_args = mock_openai_client.chat.completions.create.call_args[1]
    assert call_args["max_tokens"] == 100


def test_error_handling_invalid_temperature(llm_client):
    """Test handling of invalid temperature values."""
    with pytest.raises(ValueError):
        llm_client.query("Test", temperature=2.0)

    with pytest.raises(ValueError):
        llm_client.query("Test", temperature=-1.0)


def test_error_handling_invalid_max_tokens(llm_client):
    """Test handling of invalid max_tokens values."""
    with pytest.raises(ValueError):
        llm_client.query("Test", max_tokens=-1)


def test_empty_prompt_handling(llm_client):
    """Test handling of empty prompts."""
    with pytest.raises(ValueError):
        llm_client.query("")
