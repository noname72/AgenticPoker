import time
from unittest.mock import Mock, patch

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from agents.strategy_planner import StrategyPlanner


@pytest.fixture
def mock_openai_client():
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
                    content="""
                    {
                        "approach": "aggressive",
                        "reasoning": "Strong hand position",
                        "bet_sizing": "large",
                        "bluff_threshold": 0.7,
                        "fold_threshold": 0.2
                    }
                    """,
                    role="assistant",
                ),
            )
        ],
        usage={"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50},
    )

    client.chat.completions.create.return_value = mock_response
    return client


@pytest.fixture
def planner(mock_openai_client):
    return StrategyPlanner("Aggressive", mock_openai_client)


def test_init(planner):
    assert planner.strategy_style == "Aggressive"
    assert planner.plan_duration == 30.0
    assert planner.current_plan is None
    assert planner.plan_expiry == 0


def test_plan_strategy_success(planner):
    game_state = "pot: $200, chips: $1000, position: BB"
    plan = planner.plan_strategy(game_state, chips=1000)

    assert isinstance(plan, dict)
    assert plan["approach"] == "aggressive"
    assert plan["bet_sizing"] == "large"
    assert plan["bluff_threshold"] == 0.7
    assert plan["fold_threshold"] == 0.2


def test_plan_strategy_reuse_existing(planner):
    """Test that valid existing plans are reused"""
    print("\nTesting plan strategy reuse:")

    game_state = {"pot": 200, "chips": 1000, "position": "BB", "current_bet": 50}
    print(f"Initial game state: {game_state}")

    # First call creates plan
    print("\nCreating first plan...")
    first_plan = planner.plan_strategy(game_state, chips=1000)
    print(f"First plan: {first_plan}")

    # Ensure plan expiry is in the future
    current_time = time.time()
    print(f"\nPlan expiry: {planner.plan_expiry}")
    print(f"Current time: {current_time}")
    print(f"Time until expiry: {planner.plan_expiry - current_time} seconds")
    assert planner.plan_expiry > current_time

    # Print replanning check info
    print("\nChecking if replanning needed:")
    print(f"Current plan exists: {planner.current_plan is not None}")
    print(f"Last metrics: {planner.last_metrics}")
    needs_replan = planner.requires_replanning(game_state)
    print(f"Needs replanning: {needs_replan}")

    # Second call with similar state should reuse plan
    print("\nTrying second plan...")
    with patch.object(planner, "_query_llm") as mock_query:
        second_plan = planner.plan_strategy(game_state, chips=1000)
        mock_query.assert_not_called()
        assert second_plan == first_plan
        print("Successfully reused plan without LLM query")


def test_plan_strategy_error_fallback(planner, mock_openai_client):
    """Test fallback plan on error"""
    mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

    plan = planner.plan_strategy("game_state", chips=1000)

    assert plan["approach"] == "balanced"
    assert plan["bet_sizing"] == "medium"
    assert plan["bluff_threshold"] == 0.5
    assert plan["fold_threshold"] == 0.3


@pytest.mark.parametrize(
    "action_response,expected",
    [
        ("EXECUTE: fold because weak hand", "fold"),
        ("EXECUTE: call due to pot odds", "call"),
        ("EXECUTE: raise with strong hand", "raise"),
        ("EXECUTE: invalid_action", "call"),  # Should normalize to call
    ],
)
def test_execute_action(planner, mock_openai_client, action_response, expected):
    print("\nTesting execute_action:")
    print(f"Input action_response: {action_response}")
    print(f"Expected output: {expected}")

    # Set up the plan first
    planner.plan_strategy("game_state", chips=1000)

    # Create a game state with sufficient chips for raising
    game_state = "pot: $200, chips: $1000, current bet: $50"

    # Mock the LLM response for action execution
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
                    content=action_response,
                    role="assistant",
                ),
            )
        ],
        usage={"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50},
    )

    mock_openai_client.chat.completions.create.return_value = mock_response

    # Add debug prints for the normalization process
    print("\nDebug normalization steps:")
    action_line = action_response.split("EXECUTE:")[1].strip()
    print(f"1. Extracted action_line: {action_line}")

    normalized = planner._normalize_action(action_line)
    print(f"2. After normalization: {normalized}")

    action = planner.execute_action(game_state)
    print(f"3. Final action: {action}")

    assert action == expected, f"\nExpected: {expected}\nGot: {action}"


def test_execute_action_no_plan(planner):
    """Test execute_action falls back to 'call' with no plan"""
    action = planner.execute_action("game_state")
    assert action == "call"


def test_requires_replanning(planner):
    # Test with no current plan
    assert planner._requires_replanning("game_state") is True

    # Create a plan
    planner.plan_strategy("game_state", chips=1000)

    # Test significant changes
    assert planner._requires_replanning("pot: $5000, chips: $200") is True  # Low chips
    assert planner._requires_replanning("normal state") is False


@pytest.mark.parametrize(
    "game_state,expected",
    [
        (
            "pot: $200, chips: $1000, current bet: $50",
            {"pot": 200, "chips": 1000, "current_bet": 50},
        ),
        ("pot: $1,000, chips: $5,000", {"pot": 1000, "chips": 5000}),
        ("invalid state", {}),
    ],
)
def test_extract_game_metrics(planner, game_state, expected):
    metrics = planner._extract_game_metrics(game_state)
    assert metrics == expected


@pytest.mark.parametrize(
    "action,expected",
    [
        ("fold", "fold"),
        ("FOLD", "fold"),
        ("  call  ", "call"),
        ("RAISE", "raise"),
        ("raise with strong hand", "raise"),  # Add this test case
        ("raise 200", "raise 200"),  # Add this test case
        ("invalid", "call"),
        ("", "call"),
    ],
)
def test_normalize_action(planner, action, expected):
    print(f"\nTesting normalize_action:")
    print(f"Input: '{action}'")
    result = planner._normalize_action(action)
    print(f"Output: '{result}'")
    assert result == expected, f"\nExpected: {expected}\nGot: {result}"


def test_strategy_planner_planning():
    mock_llm = Mock()
    mock_llm.generate_plan.return_value = {
        "approach": "aggressive",
        "reasoning": "Test plan",
        "bet_sizing": "large",
        "bluff_threshold": 0.7,
        "fold_threshold": 0.2,
    }

    planner = StrategyPlanner(strategy_style="Aggressive", client=mock_llm)
    plan = planner.plan_strategy(game_state={}, chips=1000)

    assert plan.approach == "aggressive"
    assert mock_llm.generate_plan.called
