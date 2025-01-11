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
        mock_query.return_value = mock_response

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

        # Remove stack_size parameter since it's now part of game state
        plan = planner.plan_strategy(game_state)

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

    # Set initial metrics
    initial_metrics = {
        "stack_size": 1000,
        "position": "dealer",
        "phase": "pre_draw",
        "pot_size": 200,
    }
    planner.last_metrics = initial_metrics.copy()

    # Mock extract_metrics to return same metrics
    with patch.object(planner, "extract_metrics") as mock_extract:
        mock_extract.return_value = initial_metrics.copy()

        # Second call should reuse plan without generating new one
        with patch.object(planner.llm_client, "query") as mock_query:
            second_plan = planner.plan_strategy(game_state)

            mock_query.assert_not_called()
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

    plan = planner.plan_strategy(game_state)

    assert plan.approach == Approach.BALANCED
    assert plan.bet_sizing == BetSizing.MEDIUM
    assert plan.bluff_threshold == 0.5
    assert plan.fold_threshold == 0.3


def test_execute_action(planner, mock_openai_client):
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

    # Set up initial plan
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
    print(f"Set up initial plan: {planner.current_plan}")

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

        with patch.object(
            planner.llm_client, "query", return_value=response
        ) as mock_query:
            action = planner.execute_action(game_state)
            print(f"Actual action: {action}")
            print(f"Mock query called with response: {mock_query.return_value}")
            assert (
                action == expected
            ), f"Expected {expected} but got {action} for response: {response}"


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
    planner = StrategyPlanner("Aggressive", Mock())
    assert planner.current_plan is None

    # Execute action without a plan
    action = planner.get_action(game_state)

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

    # Test with no current plan
    assert planner.requires_replanning(game_state) is True

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

    # Set initial metrics
    planner.last_metrics = {
        "stack_size": 1000,
        "position": "dealer",
        "phase": "pre_draw",
        "pot_size": 0,
    }

    # Test no changes
    with patch.object(
        planner, "extract_metrics", return_value=planner.last_metrics.copy()
    ):
        assert planner.requires_replanning(game_state) is False

    # Test position change
    with patch.object(
        planner,
        "extract_metrics",
        return_value={"position": "big_blind", "stack_size": 1000},
    ):
        assert planner.requires_replanning(game_state) is True

    # Test significant stack change
    with patch.object(
        planner,
        "extract_metrics",
        return_value={"position": "dealer", "stack_size": 500},
    ):
        assert planner.requires_replanning(game_state) is True


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

    # Mock both extract_metrics and query
    with patch.object(planner, "extract_metrics") as mock_extract:
        metrics = {
            "position": PlayerPosition.BIG_BLIND.value,
            "stack_size": 1000,
            "phase": RoundPhase.PRE_DRAW.value,
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

            # Call plan_strategy without stack_size parameter
            plan = planner.plan_strategy(game_state)

            # Verify the plan was created correctly
            assert isinstance(plan, Plan)
            assert plan.approach == Approach.AGGRESSIVE
            assert plan.bet_sizing == BetSizing.LARGE
            assert plan.bluff_threshold == 0.7
            assert plan.fold_threshold == 0.2
            print("Successfully verified plan generation and LLM query")


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


def test_parse_action_response(planner):
    """Test parsing of action responses from LLM."""
    print("\nTesting action response parsing:")

    # Create a basic game state for testing
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

    # Test valid responses
    test_cases = [
        # Basic valid responses
        ("DECISION: fold", "fold"),
        ("DECISION: call", "call"),
        ("DECISION: raise 100", "raise 100"),
        # Responses with extra whitespace
        ("DECISION:    fold   ", "fold"),
        ("DECISION:   call   ", "call"),
        ("DECISION:    raise   100   ", "raise 100"),
        # Responses with mixed case
        ("DECISION: FOLD", "fold"),
        ("DECISION: CALL", "call"),
        ("DECISION: RAISE 200", "raise 200"),
        # Responses with additional text
        ("Analysis complete.\nDECISION: fold", "fold"),
        ("Strong hand detected.\nDECISION: call", "call"),
        ("Pot odds favorable.\nDECISION: raise 300", "raise 300"),
    ]

    print("Testing valid response formats:")
    for response, expected in test_cases:
        result = planner._parse_action_response(response, game_state)
        assert (
            result == expected
        ), f"Expected '{expected}' but got '{result}' for response: '{response}'"
        print(f"✓ Successfully parsed: {response} -> {result}")

    # Test invalid responses
    invalid_cases = [
        # Missing DECISION prefix
        ("fold", "call"),
        ("call", "call"),
        ("raise 100", "call"),
        # Invalid action types
        ("DECISION: check", "call"),
        ("DECISION: bet 100", "call"),
        ("DECISION: allin", "call"),
        # Invalid raise formats
        ("DECISION: raise", "call"),
        ("DECISION: raise abc", "call"),
        ("DECISION: raise -100", "call"),
        ("DECISION: raise 0", "call"),
        ("DECISION: raise 100 200", "call"),
        # Completely invalid formats
        ("", "call"),
        ("DECISION:", "call"),
        ("Invalid response", "call"),
        ("EXECUTE: fold", "call"),  # Old format
    ]

    print("\nTesting invalid response formats:")
    for response, expected in invalid_cases:
        result = planner._parse_action_response(response, game_state)
        assert (
            result == expected
        ), f"Expected '{expected}' but got '{result}' for invalid response: '{response}'"
        print(f"✓ Successfully handled invalid response: {response} -> {result}")

    # Test raise amount validation against game.min_bet
    print("\nTesting raise amount validation:")
    game_state.min_bet = 50
    response = "DECISION: raise 25"  # Below minimum bet
    result = planner._parse_action_response(response, game_state)
    assert (
        result == "call"
    ), f"Expected 'call' for raise below minimum bet, got '{result}'"
    print(f"✓ Successfully handled raise below minimum bet: {response} -> {result}")
