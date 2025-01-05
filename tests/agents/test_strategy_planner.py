import time
from unittest.mock import Mock, patch

import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from agents.strategy_planner import StrategyPlanner
from agents.types import Approach, BetSizing, Plan
from game.base_types import DeckState, PlayerPosition, PlayerState, PotState, RoundState
from game.types import GameState


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

    # Mock the LLM client's generate_plan method
    with patch.object(planner.llm_client, "generate_plan") as mock_generate_plan:
        mock_response = {
            "approach": "aggressive",
            "reasoning": "Strong hand position",
            "bet_sizing": "large",
            "bluff_threshold": 0.7,
            "fold_threshold": 0.2,
            "adjustments": [],
            "target_opponent": None,
        }
        print(f"Mock response: {mock_response}")
        mock_generate_plan.return_value = mock_response

        # Create a proper GameState object with complete PlayerState objects
        game_state = GameState(
            players=[
                PlayerState(
                    name="Player1",
                    chips=1000,
                    position=PlayerPosition.DEALER,  # Use enum value
                    bet=0,
                    folded=False,
                    is_dealer=True,
                    is_small_blind=False,
                    is_big_blind=False,
                ),
                PlayerState(
                    name="Player2",
                    chips=1000,
                    position=PlayerPosition.SMALL_BLIND,  # Use enum value
                    bet=10,
                    folded=False,
                    is_dealer=False,
                    is_small_blind=True,
                    is_big_blind=False,
                ),
                PlayerState(
                    name="Player3",
                    chips=1000,
                    position=PlayerPosition.BIG_BLIND,  # Use enum value
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

        plan = planner.plan_strategy(game_state, chips=1000)
        print(f"Generated plan: {plan}")

        # Verify the plan was created correctly
        assert isinstance(plan, Plan)
        assert (
            plan.approach == Approach.AGGRESSIVE
        ), f"Expected AGGRESSIVE but got {plan.approach}"
        assert plan.bet_sizing == BetSizing.LARGE
        assert plan.bluff_threshold == 0.7
        assert plan.fold_threshold == 0.2


def test_plan_strategy_reuse_existing(planner):
    """Test that valid existing plans are reused"""
    print("\nTesting plan strategy reuse:")

    # Create a proper GameState object
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
        ("EXECUTE: invalid_action", "call"),
    ],
)
def test_execute_action(planner, mock_openai_client, action_response, expected):
    """Test action execution with different responses"""
    print(f"\nTesting execute_action with response '{action_response}':")

    # Create initial game state
    game_state = GameState(
        players=[],
        dealer_position=0,
        small_blind=10,
        big_blind=20,
        ante=0,
        min_bet=20,
        round_state=RoundState(phase="preflop", current_bet=50, round_number=1),
        pot_state=PotState(main_pot=200),
        deck_state=DeckState(cards_remaining=52),
        active_player_position=1,
    )
    print(f"Game state: {game_state}")

    # Set up the plan first with mocked generate_plan
    with patch.object(planner.llm_client, "generate_plan") as mock_generate:
        mock_plan = {
            "approach": "aggressive",
            "reasoning": "Test plan",
            "bet_sizing": "large",
            "bluff_threshold": 0.7,
            "fold_threshold": 0.2,
            "adjustments": [],
            "target_opponent": None,
        }
        print(f"Mock plan: {mock_plan}")
        mock_generate.return_value = mock_plan

        plan = planner.plan_strategy(game_state, chips=1000)
        print(f"Generated plan: {plan}")

    # Mock the LLM client's decide_action method
    with patch.object(
        planner.llm_client, "decide_action", return_value=expected
    ) as mock_decide:
        print(f"Executing action with expected response: {expected}")
        action = planner.execute_action(game_state)
        print(f"Actual action: {action}")

        assert action == expected, f"Expected {expected} but got {action}"
        mock_decide.assert_called_once()
        args = mock_decide.call_args
        print(f"decide_action called with args: {args}")
        assert args[1]["strategy_style"] == planner.strategy_style


def test_execute_action_no_plan(planner):
    """Test execute_action falls back to 'call' with no plan"""
    game_state = GameState(
        players=[],
        dealer_position=0,
        small_blind=10,
        big_blind=20,
        ante=0,
        min_bet=20,
        round_state=RoundState(phase="preflop", current_bet=0, round_number=1),
        pot_state=PotState(main_pot=0),
        deck_state=DeckState(cards_remaining=52),
        active_player_position=1,
    )
    action = planner.execute_action(game_state)
    assert action == "call"


def test_requires_replanning(planner):
    """Test replanning trigger conditions"""
    # Create base player states
    base_players = [
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
    ]

    # Test with no current plan
    initial_state = GameState(
        players=base_players.copy(),
        dealer_position=0,
        small_blind=10,
        big_blind=20,
        ante=0,
        min_bet=20,
        round_state=RoundState(
            phase="preflop",
            current_bet=0,
            round_number=1,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=2,
            first_bettor_index=0,
        ),
        pot_state=PotState(main_pot=0),
        deck_state=DeckState(cards_remaining=52),
        active_player_position=None,
    )
    assert planner.requires_replanning(initial_state) is True

    # Mock the LLM client's generate_plan method for initial plan creation
    with patch.object(planner.llm_client, "generate_plan") as mock_generate_plan:
        mock_generate_plan.return_value = {
            "approach": "aggressive",
            "reasoning": "Test plan",
            "bet_sizing": "large",
            "bluff_threshold": 0.7,
            "fold_threshold": 0.2,
        }

        # Create initial plan and metrics
        planner.plan_strategy(initial_state, chips=1000)
        planner.last_metrics = {
            "stack_size": 1000,
            "position": PlayerPosition.BIG_BLIND.value,  # Use enum value
            "phase": "preflop",
        }

        # Test position change triggers replanning
        position_change_players = base_players.copy()
        # Change positions to simulate movement
        for player in position_change_players:
            if player.position == PlayerPosition.DEALER:
                player.position = PlayerPosition.BIG_BLIND
            elif player.position == PlayerPosition.SMALL_BLIND:
                player.position = PlayerPosition.DEALER
            elif player.position == PlayerPosition.BIG_BLIND:
                player.position = PlayerPosition.SMALL_BLIND

        position_change_state = GameState(
            players=position_change_players,
            dealer_position=1,  # Moved dealer position
            small_blind=10,
            big_blind=20,
            ante=0,
            min_bet=20,
            round_state=RoundState(
                phase="preflop",
                current_bet=0,
                round_number=1,
                dealer_position=1,
                small_blind_position=2,
                big_blind_position=0,
                first_bettor_index=1,
            ),
            pot_state=PotState(main_pot=100),
            deck_state=DeckState(cards_remaining=52),
            active_player_position=1,
        )
        assert planner.requires_replanning(position_change_state) is True

        # Test significant stack change triggers replanning
        stack_change_players = base_players.copy()
        # Modify one player's chips to trigger stack change
        stack_change_players[0].chips = 500  # Significant change from 1000

        stack_change_state = GameState(
            players=stack_change_players,  # Use players with modified stack
            dealer_position=0,
            small_blind=10,
            big_blind=20,
            ante=0,
            min_bet=20,
            round_state=RoundState(
                phase="preflop",
                current_bet=0,
                round_number=1,
                dealer_position=0,
                small_blind_position=1,
                big_blind_position=2,
                first_bettor_index=0,
            ),
            pot_state=PotState(main_pot=100),
            deck_state=DeckState(cards_remaining=52),
            active_player_position=2,  # BB position
        )
        assert planner.requires_replanning(stack_change_state) is True

        # Test no significant changes doesn't trigger replanning
        with patch.object(planner, "extract_metrics") as mock_extract:
            mock_extract.return_value = planner.last_metrics.copy()

            no_change_state = GameState(
                players=base_players.copy(),  # Use original players
                dealer_position=0,
                small_blind=10,
                big_blind=20,
                ante=0,
                min_bet=20,
                round_state=RoundState(
                    phase="preflop",
                    current_bet=0,
                    round_number=1,
                    dealer_position=0,
                    small_blind_position=1,
                    big_blind_position=2,
                    first_bettor_index=0,
                ),
                pot_state=PotState(main_pot=95),
                deck_state=DeckState(cards_remaining=52),
                active_player_position=2,  # BB position
            )
            assert planner.requires_replanning(no_change_state) is False


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

    # Mock both extract_metrics and generate_plan
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

        with patch.object(planner.llm_client, "generate_plan") as mock_generate_plan:
            mock_plan = {
                "approach": "aggressive",
                "reasoning": "Test plan",
                "bet_sizing": "large",
                "bluff_threshold": 0.7,
                "fold_threshold": 0.2,
                "adjustments": [],
                "target_opponent": None,
            }
            print(f"Mock plan: {mock_plan}")
            mock_generate_plan.return_value = mock_plan

            # Test plan generation
            plan = planner.plan_strategy(game_state, chips=1000)
            print(f"Generated plan: {plan}")

            # Verify the plan was created correctly
            assert isinstance(plan, Plan)
            assert (
                plan.approach == Approach.AGGRESSIVE
            ), f"Expected AGGRESSIVE but got {plan.approach}"
            assert plan.bet_sizing == BetSizing.LARGE
            assert plan.bluff_threshold == 0.7
            assert plan.fold_threshold == 0.2
