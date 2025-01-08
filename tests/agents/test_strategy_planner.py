import time
from unittest.mock import Mock, call, patch

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from agents.strategy_planner import StrategyPlanner
from data.states.game_state import GameState
from data.types.base_types import DeckState
from data.types.plan import Approach, BetSizing, Plan
from data.types.player_types import PlayerPosition, PlayerState
from data.types.pot_types import PotState
from data.types.round_state import RoundPhase, RoundState


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
    """Test initialization of StrategyPlanner"""
    assert planner.strategy_style == "Aggressive"
    assert planner.plan_duration == 30.0
    assert planner.current_plan is None


def test_plan_strategy_success(planner):
    """Test strategic planning functionality."""
    print("\nTesting plan strategy success:")

    # Mock the LLM client's query method
    with patch.object(planner.llm_client, "query") as mock_query:
        mock_response = """
        {
            "approach": "aggressive",
            "reasoning": "Strong hand position",
            "bet_sizing": "large", 
            "bluff_threshold": 0.7,
            "fold_threshold": 0.2
        }
        """
        print(f"Mock response: {mock_response}")
        mock_query.return_value = mock_response

        # Create a proper GameState object with complete PlayerState objects
        game_state = GameState(
            players=[
                PlayerState(
                    name="Player1",
                    chips=1000,
                    position=PlayerPosition.DEALER,
                    bet=0,
                    folded=False,
                    is_dealer=True,
                    is_small_blind=False,
                    is_big_blind=False,
                ),
                PlayerState(
                    name="Player2",
                    chips=1000,
                    position=PlayerPosition.SMALL_BLIND,
                    bet=10,
                    folded=False,
                    is_dealer=False,
                    is_small_blind=True,
                    is_big_blind=False,
                ),
                PlayerState(
                    name="Player3",
                    chips=1000,
                    position=PlayerPosition.BIG_BLIND,
                    bet=20,
                    folded=False,
                    is_dealer=False,
                    is_small_blind=False,
                    is_big_blind=True,
                ),
            ],
            dealer_position=0,
            small_blind=10,
            big_blind=20,
            ante=0,
            min_bet=20,
            round_state=RoundState(
                phase="preflop",
                current_bet=20,
                round_number=1,
                dealer_position=0,
                small_blind_position=1,
                big_blind_position=2,
                first_bettor_index=0,
            ),
            pot_state=PotState(main_pot=200),
            deck_state=DeckState(cards_remaining=52),
            active_player_position=1,
        )
        print(f"Game state: {game_state}")

        plan = planner.plan_strategy(game_state, stack_size=1000)
        print(f"Generated plan: {plan}")

        # Verify the plan was created correctly
        assert isinstance(plan, Plan)
        assert plan.approach == Approach.AGGRESSIVE
        assert plan.bet_sizing == BetSizing.LARGE
        assert plan.bluff_threshold == 0.7
        assert plan.fold_threshold == 0.2


def test_plan_strategy_reuse_existing(planner):
    """Test that valid existing plans are reused"""
    print("\nTesting plan strategy reuse:")

    # Create base game state
    game_state = GameState(
        players=[
            PlayerState(
                name="Player1",
                chips=1000,
                position=PlayerPosition.DEALER,
                bet=0,
                folded=False,
                is_dealer=True,
                is_small_blind=False,
                is_big_blind=False,
            )
        ],
        dealer_position=0,
        small_blind=10,
        big_blind=20,
        ante=0,
        min_bet=20,
        round_state=RoundState(phase="preflop", current_bet=50, round_number=1),
        pot_state=PotState(main_pot=200),
        deck_state=DeckState(cards_remaining=52),
        active_player_position=0,
    )
    print(f"Game state: {game_state}")

    # Create and set initial plan
    current_time = time.time()
    initial_plan = Plan(
        approach=Approach.AGGRESSIVE,
        reasoning="Test plan",
        bet_sizing=BetSizing.LARGE,
        bluff_threshold=0.7,
        fold_threshold=0.2,
        expiry=current_time + 30.0,
        adjustments=[],
        target_opponent=None,
    )
    planner.current_plan = initial_plan
    print(f"Initial plan: {initial_plan}")

    # Set initial metrics
    initial_metrics = {
        "stack_size": 1000,
        "position": "dealer",
        "phase": "preflop",
        "pot_size": 200,
    }
    planner.last_metrics = initial_metrics.copy()
    print(f"Initial metrics: {initial_metrics}")

    # Mock extract_metrics to return same metrics
    with patch.object(planner, "extract_metrics") as mock_extract:
        mock_extract.return_value = initial_metrics.copy()
        print(f"Mocked metrics: {initial_metrics}")

        # Second call should reuse plan without generating new one
        with patch.object(planner.llm_client, "query") as mock_query:
            second_plan = planner.plan_strategy(game_state, stack_size=1000)
            print(f"Second plan: {second_plan}")

            mock_query.assert_not_called()
            assert second_plan == initial_plan
            print("Successfully reused plan without LLM query")


def test_plan_strategy_error_fallback(planner, mock_openai_client):
    """Test fallback plan on error"""
    mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

    plan = planner.plan_strategy("game_state", stack_size=1000)

    assert plan.approach == Approach.BALANCED
    assert plan.bet_sizing == BetSizing.MEDIUM
    assert plan.bluff_threshold == 0.5
    assert plan.fold_threshold == 0.3


@pytest.mark.parametrize(
    "action_response,expected",
    [
        ("EXECUTE: fold because weak hand", "fold"),
        ("EXECUTE: call due to pot odds", "call"),
        ("EXECUTE: raise with strong hand", "raise 100"),
        ("EXECUTE: invalid_action", "call"),
    ],
)
def test_execute_action(planner, mock_openai_client, action_response, expected):
    """Test action execution with different responses"""
    print(f"\nTesting execute_action with response '{action_response}':")

    # Create initial game state
    game_state = GameState(
        players=[
            PlayerState(
                name="Player1",
                chips=1000,
                position=PlayerPosition.DEALER,
                bet=0,
                folded=False,
                is_dealer=True,
                is_small_blind=False,
                is_big_blind=False,
            )
        ],
        dealer_position=0,
        small_blind=10,
        big_blind=20,
        ante=0,
        min_bet=20,
        round_state=RoundState(phase="preflop", current_bet=50, round_number=1),
        pot_state=PotState(main_pot=200),
        deck_state=DeckState(cards_remaining=52),
        active_player_position=0,
    )
    print(f"Game state: {game_state}")

    # Set up the plan first
    current_time = time.time()
    initial_plan = Plan(
        approach=Approach.AGGRESSIVE,
        reasoning="Test plan",
        bet_sizing=BetSizing.LARGE,
        bluff_threshold=0.7,
        fold_threshold=0.2,
        expiry=current_time + 30.0,
        adjustments=[],
        target_opponent=None,
    )
    planner.current_plan = initial_plan
    print(f"Initial plan: {initial_plan}")

    # Mock the LLM client's query method directly
    with patch.object(
        planner.llm_client, "query", return_value=action_response
    ) as mock_query:
        # Execute action
        action = planner.execute_action(game_state)
        print(f"Actual action: {action}")

        assert action == expected, f"Expected {expected} but got {action}"
        mock_query.assert_called_once()


def test_execute_action_no_plan():
    """Test executing action without a plan."""
    # Create a basic player state for testing
    player_state = PlayerState(
        name="Test Player",
        chips=1000,
        bet=0,
        position=PlayerPosition.DEALER,
        folded=False
    )

    game_state = GameState(
        players=[player_state],  # Add at least one player
        dealer_position=0,
        small_blind=10,
        big_blind=20,
        ante=0,
        min_bet=20,
        round_state=RoundState(
            round_number=1,
            phase=RoundPhase.PRE_DRAW,
            current_bet=0,
            raise_count=0
        ),
        pot_state=PotState(main_pot=0),
        deck_state=DeckState(cards_remaining=52)
    )

    # Create planner without a plan
    planner = StrategyPlanner("Aggressive", Mock())
    assert planner.current_plan is None

    # Execute action without a plan
    action = planner.execute_action(game_state)

    # Should fall back to "call" when no plan exists
    assert action == "call", "Should fall back to 'call' when no plan exists"


def test_requires_replanning(planner):
    """Test replanning trigger conditions"""
    print("\nTesting replanning conditions:")

    # Create base game state
    base_state = GameState(
        players=[
            PlayerState(
                name="Player1",
                chips=1000,
                position=PlayerPosition.DEALER,
                bet=0,
                folded=False,
                is_dealer=True,
                is_small_blind=False,
                is_big_blind=False,
            )
        ],
        dealer_position=0,
        small_blind=10,
        big_blind=20,
        ante=0,
        min_bet=20,
        round_state=RoundState(phase="preflop", current_bet=0, round_number=1),
        pot_state=PotState(main_pot=0),
        deck_state=DeckState(cards_remaining=52),
        active_player_position=0,
    )

    # Test with no current plan
    print("Testing with no current plan:")
    with patch.object(planner, "extract_metrics") as mock_extract:
        mock_extract.return_value = {
            "stack_size": 1000,
            "position": "dealer",  # Use string value
            "phase": "preflop",
            "pot_size": 0,
        }
        assert planner.requires_replanning(base_state) is True
        print("Correctly requires replanning with no plan")

    # Create and set initial plan
    current_time = time.time()
    initial_plan = Plan(
        approach=Approach.AGGRESSIVE,
        reasoning="Test plan",
        bet_sizing=BetSizing.LARGE,
        bluff_threshold=0.7,
        fold_threshold=0.2,
        expiry=current_time + 30.0,  # Set expiry in the future
        adjustments=[],
        target_opponent=None,
    )
    planner.current_plan = initial_plan
    print(f"Created initial plan: {initial_plan}")

    # Set up initial metrics
    initial_metrics = {
        "stack_size": 1000,
        "position": "dealer",  # Use string value
        "phase": "preflop",
        "pot_size": 0,
    }
    planner.last_metrics = initial_metrics.copy()
    print(f"Initial metrics set: {initial_metrics}")

    # Test no significant changes
    with patch.object(planner, "extract_metrics") as mock_extract:
        mock_extract.return_value = initial_metrics.copy()
        result = planner.requires_replanning(base_state)
        print(f"Current metrics: {mock_extract.return_value}")
        print(f"Last metrics: {planner.last_metrics}")
        print(f"Current plan expired: {planner.current_plan.is_expired()}")
        assert result is False, "Should not replan when metrics haven't changed"
        print("Correctly does not replan with no changes")

    # Test position change
    with patch.object(planner, "extract_metrics") as mock_extract:
        changed_metrics = initial_metrics.copy()
        changed_metrics["position"] = "big_blind"  # Use string value
        mock_extract.return_value = changed_metrics
        assert planner.requires_replanning(base_state) is True
        print("Correctly requires replanning on position change")

    # Test significant stack change
    with patch.object(planner, "extract_metrics") as mock_extract:
        changed_metrics = initial_metrics.copy()
        changed_metrics["stack_size"] = 500  # Changed by more than threshold
        mock_extract.return_value = changed_metrics
        assert planner.requires_replanning(base_state) is True
        print("Correctly requires replanning on significant stack change")

    # Test small stack change (shouldn't trigger replan)
    with patch.object(planner, "extract_metrics") as mock_extract:
        changed_metrics = initial_metrics.copy()
        changed_metrics["stack_size"] = 1050  # Small change
        mock_extract.return_value = changed_metrics
        assert planner.requires_replanning(base_state) is False
        print("Correctly does not replan on small stack change")


def test_strategy_planner_planning():
    """Test strategy planning with mocked LLM client"""
    print("\nTesting strategy planner planning:")

    # Create mock LLM client and OpenAI client
    mock_openai = Mock()
    planner = StrategyPlanner(strategy_style="Aggressive", client=mock_openai)
    print(f"Created planner with strategy style: {planner.strategy_style}")

    # Create a proper GameState object with complete PlayerState objects
    game_state = GameState(
        players=[
            PlayerState(
                name="Player1",
                chips=1000,
                position=PlayerPosition.DEALER,
                bet=0,
                folded=False,
                is_dealer=True,
                is_small_blind=False,
                is_big_blind=False,
            ),
            PlayerState(
                name="Player2",
                chips=1000,
                position=PlayerPosition.SMALL_BLIND,
                bet=10,
                folded=False,
                is_dealer=False,
                is_small_blind=True,
                is_big_blind=False,
            ),
            PlayerState(
                name="Player3",
                chips=1000,
                position=PlayerPosition.BIG_BLIND,
                bet=20,
                folded=False,
                is_dealer=False,
                is_small_blind=False,
                is_big_blind=True,
            ),
        ],
        dealer_position=0,
        small_blind=10,
        big_blind=20,
        ante=0,
        min_bet=20,
        round_state=RoundState(
            phase="preflop",
            current_bet=50,
            round_number=1,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=2,
            first_bettor_index=0,
        ),
        pot_state=PotState(main_pot=200),
        deck_state=DeckState(cards_remaining=52),
        active_player_position=1,
    )
    print(f"Game state: {game_state}")

    # Mock both extract_metrics and query
    with patch.object(planner, "extract_metrics") as mock_extract:
        metrics = {
            "position": PlayerPosition.BIG_BLIND.value,
            "stack_size": 1000,
            "phase": "preflop",
            "pot_size": 100,
            "current_bet": 50,
        }
        print(f"Mock metrics: {metrics}")
        mock_extract.return_value = metrics

        with patch.object(planner.llm_client, "query") as mock_query:
            mock_response = """
            {
                "approach": "aggressive",
                "reasoning": "Test plan",
                "bet_sizing": "large",
                "bluff_threshold": 0.7,
                "fold_threshold": 0.2
            }
            """
            print(f"Mock response: {mock_response}")
            mock_query.return_value = mock_response

            # Test plan generation
            plan = planner.plan_strategy(game_state, stack_size=1000)
            print(f"Generated plan: {plan}")

            # Verify the plan was created correctly
            assert isinstance(plan, Plan)
            assert (
                plan.approach == Approach.AGGRESSIVE
            ), f"Expected AGGRESSIVE but got {plan.approach}"
            assert plan.bet_sizing == BetSizing.LARGE
            assert plan.bluff_threshold == 0.7
            assert plan.fold_threshold == 0.2

            # Verify query was called with correct arguments
            mock_query.assert_called_once()
            args = mock_query.call_args
            assert args[1]["temperature"] == 0.7
            assert args[1]["max_tokens"] == 200
            print("Successfully verified plan generation and LLM query")


def test_validate_plan_data(planner):
    """Test plan data validation"""
    print("\nTesting plan data validation:")

    # Test valid plan data
    valid_plan = {
        "approach": "aggressive",
        "reasoning": "Test plan",
        "bet_sizing": "large",
        "bluff_threshold": 0.7,
        "fold_threshold": 0.2,
        "adjustments": [],
        "target_opponent": None,
    }
    print(f"Testing valid plan: {valid_plan}")

    validated = planner._validate_plan_data(valid_plan)
    assert validated["approach"] == Approach.AGGRESSIVE
    assert validated["bet_sizing"] == BetSizing.LARGE
    assert validated["bluff_threshold"] == 0.7
    print("Valid plan passed validation")

    # Test missing required field
    invalid_plan = valid_plan.copy()
    del invalid_plan["approach"]
    print(f"\nTesting plan with missing field: {invalid_plan}")

    with pytest.raises(ValueError, match="Missing required field: approach"):
        planner._validate_plan_data(invalid_plan)
    print("Missing field correctly detected")

    # Test invalid enum value
    invalid_plan = valid_plan.copy()
    invalid_plan["approach"] = "invalid_approach"
    print(f"\nTesting plan with invalid enum: {invalid_plan}")

    with pytest.raises(ValueError, match="Invalid value for approach"):
        planner._validate_plan_data(invalid_plan)
    print("Invalid enum value correctly detected")

    # Test invalid threshold range
    invalid_plan = valid_plan.copy()
    invalid_plan["bluff_threshold"] = 1.5
    print(f"\nTesting plan with invalid threshold: {invalid_plan}")

    with pytest.raises(ValueError, match="Invalid range for bluff_threshold"):
        planner._validate_plan_data(invalid_plan)
    print("Invalid threshold range correctly detected")


def test_create_fallback_plan(planner):
    """Test fallback plan creation"""
    print("\nTesting fallback plan creation:")

    current_time = time.time()
    reason = "Test fallback reason"

    plan = planner._create_fallback_plan(current_time, reason)

    assert isinstance(plan, Plan)
    assert plan.approach == Approach.BALANCED
    assert plan.bet_sizing == BetSizing.MEDIUM
    assert plan.bluff_threshold == 0.5
    assert plan.fold_threshold == 0.3
    assert reason in plan.reasoning
    assert plan.expiry == current_time + planner.plan_duration
    print("Fallback plan created with correct attributes")


def test_plan_expiration(planner):
    """Test plan expiration logic"""
    print("\nTesting plan expiration:")

    current_time = time.time()

    # Create a plan that expires in 5 seconds
    plan = Plan(
        approach=Approach.AGGRESSIVE,
        reasoning="Test plan",
        bet_sizing=BetSizing.LARGE,
        bluff_threshold=0.7,
        fold_threshold=0.2,
        expiry=current_time + 5.0,
        adjustments=[],
        target_opponent=None,
    )
    print(f"Created plan expiring in 5 seconds")

    # Test not expired
    assert not plan.is_expired(current_time)
    assert not plan.is_expired(current_time + 4.9)
    print("Plan correctly shows as not expired")

    # Test expired
    assert plan.is_expired(current_time + 5.1)
    print("Plan correctly shows as expired")

    # Test default current_time
    time.sleep(0.1)  # Ensure some time has passed
    not_expired_plan = Plan(
        approach=Approach.AGGRESSIVE,
        reasoning="Test plan",
        bet_sizing=BetSizing.LARGE,
        bluff_threshold=0.7,
        fold_threshold=0.2,
        expiry=time.time() + 1.0,  # Expires in 1 second
        adjustments=[],
        target_opponent=None,
    )
    assert not not_expired_plan.is_expired()  # Should use current time
    print("Plan expiration works with default current_time")

    # Test expired plan with default current_time
    expired_plan = Plan(
        approach=Approach.AGGRESSIVE,
        reasoning="Test plan",
        bet_sizing=BetSizing.LARGE,
        bluff_threshold=0.7,
        fold_threshold=0.2,
        expiry=time.time() - 1.0,  # Expired 1 second ago
        adjustments=[],
        target_opponent=None,
    )
    assert expired_plan.is_expired()  # Should use current time
    print("Expired plan detected with default current_time")
