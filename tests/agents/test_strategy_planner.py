import time
from unittest.mock import Mock, patch

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from agents.strategy_planner import StrategyPlanner
from agents.types import Approach, BetSizing, Plan


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
    """Test strategic planning functionality."""
    game_state = "pot: $200, chips: $1000, position: BB"
    plan = planner.plan_strategy(game_state, chips=1000)

    # Update assertions to check Plan object instead of dict
    assert isinstance(plan, Plan)
    assert plan.approach == Approach.AGGRESSIVE
    assert plan.bet_sizing == BetSizing.LARGE
    assert plan.bluff_threshold == 0.7
    assert plan.fold_threshold == 0.2


def test_plan_strategy_reuse_existing(planner):
    """Test that valid existing plans are reused"""
    print("\nTesting plan strategy reuse:")

    game_state = {"pot": 200, "chips": 1000, "position": "BB", "current_bet": 50}
    print(f"Initial game state: {game_state}")

    # First call creates plan
    print("\nCreating first plan...")
    first_plan = planner.plan_strategy(game_state, chips=1000)
    print(f"First plan: {first_plan}")

    # Check plan expiry through Plan object
    current_time = time.time()
    print(f"\nPlan expiry: {first_plan.expiry}")
    print(f"Current time: {current_time}")
    print(f"Time until expiry: {first_plan.expiry - current_time} seconds")
    assert first_plan.expiry > current_time

    # Print replanning check info
    print("\nChecking if replanning needed:")
    print(f"Current plan exists: {planner.current_plan is not None}")
    print(f"Last metrics: {planner.last_metrics}")
    needs_replan = planner.requires_replanning(game_state)
    print(f"Needs replanning: {needs_replan}")

    # Second call with similar state should reuse plan
    print("\nTrying second plan...")
    with patch.object(planner.llm_client, "generate_plan") as mock_generate:
        second_plan = planner.plan_strategy(game_state, chips=1000)
        mock_generate.assert_not_called()
        assert second_plan == first_plan
        print("Successfully reused plan without LLM query")


def test_plan_strategy_error_fallback(planner, mock_openai_client):
    """Test fallback plan on error"""
    mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

    plan = planner.plan_strategy("game_state", chips=1000)

    assert plan.approach == Approach.BALANCED
    assert plan.bet_sizing == BetSizing.MEDIUM
    assert plan.bluff_threshold == 0.5
    assert plan.fold_threshold == 0.3


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
    """Test replanning trigger conditions"""
    # Test with no current plan
    assert planner.requires_replanning("game_state") is True

    # Create initial plan and metrics
    game_state = {"pot": 100, "position": "BB", "stack_size": 1000, "phase": "preflop"}
    planner.plan_strategy(game_state, chips=1000)
    planner.last_metrics = {"stack_size": 1000, "position": "BB"}

    # Test position change triggers replanning
    position_change_state = {
        "pot": 100,
        "position": "SB",  # Changed position
        "stack_size": 1000,
        "phase": "preflop",
    }
    assert planner.requires_replanning(position_change_state) is True

    # Test significant stack change triggers replanning
    stack_change_state = {
        "pot": 100,
        "position": "BB",
        "stack_size": 800,  # Changed by more than REPLAN_STACK_THRESHOLD
        "phase": "preflop",
    }
    assert planner.requires_replanning(stack_change_state) is True

    # Test no significant changes doesn't trigger replanning
    no_change_state = {
        "pot": 100,
        "position": "BB",
        "stack_size": 950,  # Small change, less than threshold
        "phase": "preflop",
    }
    assert planner.requires_replanning(no_change_state) is False


def test_strategy_planner_planning():
    """Test strategy planning with mocked LLM client"""
    # Create mock LLM client
    mock_llm_client = Mock()
    mock_llm_client.generate_plan.return_value = {
        "approach": "aggressive",  # String value that will be converted to enum
        "reasoning": "Test plan",
        "bet_sizing": "large",  # String value that will be converted to enum
        "bluff_threshold": 0.7,
        "fold_threshold": 0.2,
    }

    # Create planner with mocked OpenAI client
    mock_openai = Mock()
    planner = StrategyPlanner(strategy_style="Aggressive", client=mock_openai)

    # Replace the LLM client with our mock
    planner.llm_client = mock_llm_client

    # Test plan generation
    plan = planner.plan_strategy(game_state={}, chips=1000)

    # Verify the plan was created correctly
    assert plan.approach == Approach.AGGRESSIVE
    assert plan.bet_sizing == BetSizing.LARGE
    assert plan.bluff_threshold == 0.7
    assert plan.fold_threshold == 0.2
    assert mock_llm_client.generate_plan.called

    # Verify the arguments passed to generate_plan
    mock_llm_client.generate_plan.assert_called_once()
    args = mock_llm_client.generate_plan.call_args
    assert args[1]["strategy_style"] == "Aggressive"  # Check kwargs
