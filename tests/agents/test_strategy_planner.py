import time
from unittest.mock import patch, Mock

import pytest

from agents.strategy_planner import StrategyPlanner
from data.types.plan import Approach, BetSizing, Plan


@pytest.fixture
def strategy_planner():
    """Create a strategy planner instance for testing.

    Assumptions:
        - Strategy style "aggressive" is a valid style
        - Default plan duration of 30.0 seconds is reasonable for testing
        - Default replan threshold of 100 chips is appropriate
    """
    return StrategyPlanner(strategy_style="aggressive")


@pytest.fixture
def mock_plan():
    """Create a mock plan for testing.

    Assumptions:
        - Plan expiry is set 30 seconds in the future
        - Approach.AGGRESSIVE is a valid approach
        - BetSizing.MEDIUM is a valid bet sizing
        - Bluff/fold thresholds between 0-1 are valid
        - Empty adjustments list is valid
        - None is valid for target_opponent
    """
    return Plan(
        approach=Approach.AGGRESSIVE,
        reasoning="Test reasoning",
        bet_sizing=BetSizing.MEDIUM,
        bluff_threshold=0.4,
        fold_threshold=0.3,
        expiry=time.time() + 30.0,
        adjustments=[],
        target_opponent=None,
    )


def test_strategy_planner_initialization():
    """Test StrategyPlanner initialization with different parameters.

    Tests both default and custom initialization parameters.

    Assumptions:
        - "aggressive" and "conservative" are valid strategy styles
        - Plan duration can be modified from default
        - Replan threshold can be modified from default
        - current_plan starts as None
        - last_metrics starts as None
    """
    # Test default initialization
    planner = StrategyPlanner(strategy_style="aggressive")
    assert planner.strategy_style == "aggressive"
    assert planner.plan_duration == 30.0
    assert planner.REPLAN_STACK_THRESHOLD == 100
    assert planner.current_plan is None
    assert planner.last_metrics is None

    # Test custom initialization
    planner = StrategyPlanner(
        strategy_style="conservative",
        plan_duration=60.0,
        replan_threshold=200,
    )
    assert planner.strategy_style == "conservative"
    assert planner.plan_duration == 60.0
    assert planner.REPLAN_STACK_THRESHOLD == 200


def test_create_default_plan(strategy_planner):
    """Test creation of default plan when errors occur.

    Verifies the default plan has expected conservative values.

    Assumptions:
        - Approach.BALANCED is appropriate default approach
        - BetSizing.MEDIUM is appropriate default sizing
        - 0.5 bluff and 0.3 fold thresholds are appropriate defaults
        - Plan expiry is set in the future
        - Empty adjustments list is appropriate default
        - None is appropriate default target_opponent
    """
    default_plan = strategy_planner._create_default_plan()

    assert default_plan.approach == Approach.BALANCED
    assert default_plan.bet_sizing == BetSizing.MEDIUM
    assert default_plan.bluff_threshold == 0.5
    assert default_plan.fold_threshold == 0.3
    assert default_plan.reasoning == "Default fallback plan due to error"
    assert default_plan.adjustments == []
    assert default_plan.target_opponent is None
    assert default_plan.expiry > time.time()


def test_create_plan_from_response(strategy_planner):
    """Test plan creation from LLM response data.

    Verifies proper conversion of dictionary data to Plan object.

    Assumptions:
        - LLM response contains all required plan fields
        - String values map to valid enum values
        - Numeric thresholds are between 0-1
        - Plan expiry is automatically set
        - Missing optional fields use defaults
    """
    plan_data = {
        "approach": "aggressive",
        "reasoning": "Test reasoning",
        "bet_sizing": "large",
        "bluff_threshold": 0.6,
        "fold_threshold": 0.2,
    }

    plan = strategy_planner._create_plan_from_response(plan_data)

    assert plan.approach == Approach.AGGRESSIVE
    assert plan.reasoning == "Test reasoning"
    assert plan.bet_sizing == BetSizing.LARGE
    assert plan.bluff_threshold == 0.6
    assert plan.fold_threshold == 0.2
    assert plan.expiry > time.time()


def test_create_plan_from_response_with_missing_fields(strategy_planner):
    """Test plan creation with missing optional fields in response data.

    Verifies default values are used when fields are missing.

    Assumptions:
        - Plan creation handles missing optional fields gracefully
        - Default values are used for missing fields
        - Required fields must be present
    """
    # Minimal plan data with only required fields
    plan_data = {
        "approach": "balanced",
        "reasoning": "Test reasoning",
    }

    plan = strategy_planner._create_plan_from_response(plan_data)

    assert plan.approach == Approach.BALANCED
    assert plan.reasoning == "Test reasoning"
    assert plan.bet_sizing == BetSizing.MEDIUM  # Default
    assert plan.bluff_threshold == 0.5  # Default
    assert plan.fold_threshold == 0.3  # Default
    assert plan.expiry > time.time()
    assert plan.adjustments == []
    assert plan.target_opponent is None


def test_requires_replanning_no_current_plan(strategy_planner, mock_game, mock_player):
    """Test replanning requirement when no current plan exists.

    Assumptions:
        - mock_game provides required game state interface
        - mock_player provides required player interface
        - No current plan should always trigger replanning
    """
    assert strategy_planner.requires_replanning(mock_game, mock_player) is True


def test_requires_replanning_expired_plan(
    strategy_planner, mock_game, mock_player, mock_plan
):
    """Test replanning requirement when current plan is expired.

    Assumptions:
        - Plan expiry is checked against current time
        - Expired plan (expiry < current time) should trigger replanning
        - New Plan instances can be created with different expiry times
    """
    # Create expired plan
    expired_plan = Plan(
        approach=mock_plan.approach,
        reasoning=mock_plan.reasoning,
        bet_sizing=mock_plan.bet_sizing,
        bluff_threshold=mock_plan.bluff_threshold,
        fold_threshold=mock_plan.fold_threshold,
        expiry=time.time() - 1.0,  # Expired
        adjustments=mock_plan.adjustments,
        target_opponent=mock_plan.target_opponent,
    )
    strategy_planner.current_plan = expired_plan

    assert strategy_planner.requires_replanning(mock_game, mock_player) is True


def test_requires_replanning_valid_plan(
    strategy_planner, mock_game, mock_player, mock_plan
):
    """Test replanning requirement when current plan is still valid.

    Assumptions:
        - Plan expiry is checked against current time
        - Valid plan (expiry > current time) should not trigger replanning
        - New Plan instances can be created with different expiry times
    """
    # Create valid plan
    valid_plan = Plan(
        approach=mock_plan.approach,
        reasoning=mock_plan.reasoning,
        bet_sizing=mock_plan.bet_sizing,
        bluff_threshold=mock_plan.bluff_threshold,
        fold_threshold=mock_plan.fold_threshold,
        expiry=time.time() + 30.0,  # Valid
        adjustments=mock_plan.adjustments,
        target_opponent=mock_plan.target_opponent,
    )
    strategy_planner.current_plan = valid_plan

    assert strategy_planner.requires_replanning(mock_game, mock_player) is False


@patch("agents.llm_response_generator.LLMResponseGenerator.generate_plan")
def test_plan_strategy_success(
    mock_generate_plan, strategy_planner, mock_game, mock_player
):
    """Test successful strategy planning.

    Verifies proper plan creation from LLM response.

    Assumptions:
        - LLMResponseGenerator.generate_plan can be mocked
        - Generated plan data contains all required fields
        - mock_game provides get_state() method
        - mock_player provides required interface
        - Plan is created and stored in strategy_planner
    """
    # Mock the plan generation
    plan_data = {
        "approach": "aggressive",
        "reasoning": "Test reasoning",
        "bet_sizing": "large",
        "bluff_threshold": 0.6,
        "fold_threshold": 0.2,
    }
    mock_generate_plan.return_value = plan_data

    # Execute planning
    strategy_planner.plan_strategy(mock_player, mock_game)

    # Verify plan was created
    assert strategy_planner.current_plan is not None
    assert strategy_planner.current_plan.approach == Approach.AGGRESSIVE
    assert strategy_planner.current_plan.bet_sizing == BetSizing.LARGE
    mock_generate_plan.assert_called_once()


@patch("agents.llm_response_generator.LLMResponseGenerator.generate_plan")
def test_plan_strategy_error_handling(
    mock_generate_plan, strategy_planner, mock_game, mock_player
):
    """Test error handling during strategy planning.

    Verifies fallback to default plan on error.

    Assumptions:
        - LLMResponseGenerator.generate_plan can raise exceptions
        - Errors are caught and handled gracefully
        - Default plan is created as fallback
        - StrategyLogger is available for error logging
    """
    # Mock plan generation to raise an error
    mock_generate_plan.side_effect = Exception("Test error")

    # Execute planning
    strategy_planner.plan_strategy(mock_player, mock_game)

    # Verify fallback to default plan
    assert strategy_planner.current_plan is not None
    assert strategy_planner.current_plan.approach == Approach.BALANCED
    assert strategy_planner.current_plan.bet_sizing == BetSizing.MEDIUM
    mock_generate_plan.assert_called_once()


@patch("agents.llm_response_generator.LLMResponseGenerator.generate_plan")
def test_plan_strategy_reuse(
    mock_generate_plan, strategy_planner, mock_game, mock_player, mock_plan
):
    """Test plan reuse when current plan is still valid.

    Verifies that valid plans are reused without generating new ones.

    Assumptions:
        - Current plan's expiry is checked for validity
        - Valid plans are reused without modification
        - LLMResponseGenerator.generate_plan is not called for reused plans
        - StrategyLogger is available for plan reuse logging
        - New Plan instances can be created with different expiry times
    """
    # Create valid current plan
    valid_plan = Plan(
        approach=mock_plan.approach,
        reasoning=mock_plan.reasoning,
        bet_sizing=mock_plan.bet_sizing,
        bluff_threshold=mock_plan.bluff_threshold,
        fold_threshold=mock_plan.fold_threshold,
        expiry=time.time() + 30.0,  # Valid
        adjustments=mock_plan.adjustments,
        target_opponent=mock_plan.target_opponent,
    )
    strategy_planner.current_plan = valid_plan

    # Execute planning
    strategy_planner.plan_strategy(mock_player, mock_game)

    # Verify plan was reused and no new plan was generated
    assert strategy_planner.current_plan == valid_plan
    mock_generate_plan.assert_not_called()


def test_requires_replanning_with_error():
    """Test replanning check when an error occurs.

    Verifies safe error handling in requires_replanning.

    Assumptions:
        - Method handles exceptions gracefully
        - Returns False on error to keep current plan
        - Logs error through StrategyLogger
    """
    planner = StrategyPlanner(strategy_style="aggressive")

    # Create a valid current plan first
    current_plan = Plan(
        approach=Approach.BALANCED,
        reasoning="Test reasoning",
        bet_sizing=BetSizing.MEDIUM,
        bluff_threshold=0.5,
        fold_threshold=0.3,
        expiry=time.time() + 30.0,
        adjustments=[],
        target_opponent=None,
    )
    planner.current_plan = current_plan

    mock_game = Mock()
    # Set up the mock to raise an exception when get_state() is called
    mock_game.get_state = Mock(side_effect=Exception("Test error"))
    mock_player = Mock()

    # Should return False (keep current plan) on error
    assert planner.requires_replanning(mock_game, mock_player) is False


@patch("agents.llm_response_generator.LLMResponseGenerator.generate_plan")
def test_plan_strategy_with_hand_eval(
    mock_generate_plan, strategy_planner, mock_game, mock_player
):
    """Test strategy planning with hand evaluation provided.

    Verifies planning works with optional hand evaluation parameter.

    Assumptions:
        - HandEvaluation object can be passed to plan_strategy
        - LLMResponseGenerator receives hand evaluation in generate_plan
        - Planning proceeds normally with hand evaluation
    """
    plan_data = {
        "approach": "aggressive",
        "reasoning": "Strong hand",
        "bet_sizing": "large",
        "bluff_threshold": 0.6,
        "fold_threshold": 0.2,
    }
    mock_generate_plan.return_value = plan_data

    mock_hand_eval = Mock()
    strategy_planner.plan_strategy(mock_player, mock_game, hand_eval=mock_hand_eval)

    mock_generate_plan.assert_called_once_with(
        player=mock_player, game_state=mock_game.get_state(), hand_eval=mock_hand_eval
    )
