import time
from unittest.mock import Mock, call, patch

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from agents.strategy_planner import StrategyPlanner
from data.states.game_state import GameState
from data.states.player_state import PlayerState
from data.states.round_state import RoundPhase, RoundState
from data.types.base_types import DeckState
from data.types.plan import Approach, BetSizing, Plan
from data.types.player_types import PlayerPosition
from data.types.pot_types import PotState


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
    return StrategyPlanner("Aggressive")


def test_init(planner):
    """Test initialization of StrategyPlanner"""
    assert planner.strategy_style == "Aggressive"


def test_plan_strategy_success(planner):
    """Test strategic planning functionality."""
    print("\nTesting plan strategy success:")

    # Create a proper Game object with complete state
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
            phase=RoundPhase.PRE_DRAW,
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

    plan = planner.plan_strategy(game_state, game_state.players[0])

    assert isinstance(plan, Plan)
    assert plan.approach == Approach.AGGRESSIVE
    assert plan.bet_sizing == BetSizing.LARGE
    assert plan.bluff_threshold == 0.7
    assert plan.fold_threshold == 0.2


def test_plan_strategy_reuse_existing(planner):
    """Test that valid existing plans are reused"""
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
        round_state=RoundState(
            phase=RoundPhase.PRE_DRAW,
            current_bet=50,
            round_number=1,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=2,
            first_bettor_index=0,
        ),
        pot_state=PotState(main_pot=200),
        deck_state=DeckState(cards_remaining=52),
        active_player_position=0,
    )

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

    # Second call should reuse plan without generating new one
    second_plan = planner.plan_strategy(game_state, game_state.players[0])
    assert second_plan == initial_plan


def test_plan_strategy_error_fallback(planner, mock_openai_client):
    """Test fallback plan on error"""
    mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

    # Create a basic game state
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
        round_state=RoundState(
            phase=RoundPhase.PRE_DRAW,
            current_bet=0,
            round_number=1,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=2,
            first_bettor_index=0,
        ),
        pot_state=PotState(main_pot=0),
        deck_state=DeckState(cards_remaining=52),
        active_player_position=0,
    )

    plan = planner.plan_strategy(game_state, game_state.players[0])

    assert plan.approach == Approach.BALANCED
    assert plan.bet_sizing == BetSizing.MEDIUM
    assert plan.bluff_threshold == 0.5
    assert plan.fold_threshold == 0.3


def test_execute_action(planner):
    """Test action execution with different responses"""
    print("\nTesting action execution:")

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
        round_state=RoundState(
            phase=RoundPhase.PRE_DRAW,
            current_bet=50,
            round_number=1,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=2,
            first_bettor_index=0,
        ),
        pot_state=PotState(main_pot=200),
        deck_state=DeckState(cards_remaining=52),
        active_player_position=0,
    )
    print(
        f"Created game state with active player position: {game_state.active_player_position}"
    )

    # Test cases with exact response format
    test_cases = [
        (
            "Analyzing weak hand...\nDECISION: fold weak hand against aggressive raise",
            "fold",
        ),
        (
            "Calculating pot odds...\nDECISION: call decent draw with good pot odds",
            "call",
        ),
        (
            "Strong hand detected...\nDECISION: raise 100 strong hand in position",
            "raise 100",
        ),
        ("Unclear situation...\nDECISION: call marginal hand", "call"),  # Valid call
    ]

    for i, (response, expected) in enumerate(test_cases):
        print(f"\nTest case {i+1}:")
        print(f"Response: {repr(response)}")
        print(f"Expected action: {expected}")

        player = game_state.players[0]
        action = planner.execute_action(game_state, player)
        assert action == expected, f"Expected {expected} but got {action}"


def test_execute_action_no_plan():
    """Test executing action without a plan."""
    # Create a basic player state for testing
    player_state = PlayerState(
        name="Test Player",
        chips=1000,
        bet=0,
        position=PlayerPosition.DEALER,
        folded=False,
    )

    game_state = GameState(
        players=[player_state],  # Add at least one player
        dealer_position=0,
        small_blind=10,
        big_blind=20,
        ante=0,
        min_bet=20,
        round_state=RoundState(
            round_number=1, phase=RoundPhase.PRE_DRAW, current_bet=0, raise_count=0
        ),
        pot_state=PotState(main_pot=0),
        deck_state=DeckState(cards_remaining=52),
    )

    # Create planner without a plan
    planner = StrategyPlanner("Aggressive")
    assert planner.current_plan is None

    # Use execute_action instead of get_action
    player = game_state.players[0]
    action = planner.execute_action(game_state, player)

    # Should fall back to "call" when no plan exists
    assert action == "call", "Should fall back to 'call' when no plan exists"


def test_requires_replanning(planner):
    """Test replanning trigger conditions"""
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
        round_state=RoundState(
            phase=RoundPhase.PRE_DRAW,
            current_bet=0,
            round_number=1,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=2,
            first_bettor_index=0,
        ),
        pot_state=PotState(main_pot=0),
        deck_state=DeckState(cards_remaining=52),
        active_player_position=0,
    )

    player = game_state.players[0]

    # Test with no current plan
    assert planner.requires_replanning(game_state, player) is True

    # Create and set initial plan
    current_time = time.time()
    planner.current_plan = Plan(
        approach=Approach.AGGRESSIVE,
        reasoning="Test plan",
        bet_sizing=BetSizing.LARGE,
        bluff_threshold=0.7,
        fold_threshold=0.2,
        expiry=current_time + 30.0,
        adjustments=[],
        target_opponent=None,
    )

    # Test no changes
    assert planner.requires_replanning(game_state, player) is False

    # Test position change
    game_state.players[0].position = PlayerPosition.BIG_BLIND
    assert planner.requires_replanning(game_state, player) is True

    # Test significant stack change
    game_state.players[0].chips = 500
    assert planner.requires_replanning(game_state, player) is True


def test_strategy_planner_planning():
    """Test strategy planning with mocked game state"""
    print("\nTesting strategy planner planning:")

    # Create mock LLM client and OpenAI client
    mock_openai = Mock()
    planner = StrategyPlanner(strategy_style="Aggressive")
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
            phase=RoundPhase.PRE_DRAW,
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

    # Call plan_strategy directly without mocking
    player = game_state.players[0]
    plan = planner.plan_strategy(game_state, player)

    # Verify the plan was created correctly
    assert isinstance(plan, Plan)
    assert plan.approach == Approach.AGGRESSIVE
    assert plan.bet_sizing == BetSizing.LARGE
    assert plan.bluff_threshold == 0.7
    assert plan.fold_threshold == 0.2
    print("Successfully verified plan generation")


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
