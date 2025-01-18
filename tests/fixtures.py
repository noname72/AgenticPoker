"""Standard pytest fixtures for testing poker game components.

This module provides reusable pytest fixtures for testing the poker game implementation.
The fixtures create mock objects and test configurations that can be used across test files.

Usage:
    These fixtures are automatically available to all test files through conftest.py.
    Simply declare the fixture name as a test parameter to use it:

    def test_agent_decision(mock_agent, mock_game_state):
        action = mock_agent.decide_action(mock_game_state)
        assert action is not None

Available Fixtures:
    mock_agent: A basic MockAgent instance with default configuration
    mock_agents: List of MockAgents with different strategies
    mock_betting: MockBetting instance with pre-configured betting results
    mock_deck: MockDeck instance for simulating card dealing
    mock_hand: MockHand instance for testing hand evaluation
    mock_llm_client: MockLLMClient for testing AI interactions
    mock_llm_response_generator: MockLLMResponseGenerator for testing AI responses
    mock_player: Basic MockPlayer instance
    mock_players: List of MockPlayers for testing multiplayer scenarios
    mock_player_queue: MockPlayerQueue configured with mock_players
    mock_pot_manager: MockPotManager for testing pot management
    mock_strategy_planner: MockStrategyPlanner with aggressive strategy
    mock_game_state: GameState instance with default test configuration
    mock_game: Mock game instance with common components configured

Auto-use Fixtures:
    setup_test_env: Configures environment variables for testing
    setup_logging: Configures logging for test execution

Example:
    # Test agent decision making
    def test_agent_makes_valid_decision(mock_agent, mock_game_state):
        action = mock_agent.decide_action(mock_game_state)
        assert action.action_type in [ActionType.CALL, ActionType.FOLD, ActionType.RAISE]

    # Test betting round
    def test_betting_round(mock_betting, mock_players, mock_game):
        pot, side_pots, continue_game = mock_betting.handle_betting_round(mock_game)
        assert isinstance(pot, int)
        assert pot >= 0

    # Test player queue rotation
    def test_player_rotation(mock_player_queue):
        first_player = mock_player_queue.get_next_player()
        assert first_player.name == "Player1"
        second_player = mock_player_queue.get_next_player()
        assert second_player.name == "Player2"

Note:
    - All fixtures are function-scoped by default
    - Auto-use fixtures run automatically for all tests
    - Mock objects are configured with reasonable defaults but can be customized
    - Use fixture factories when you need parameterized fixtures
"""

from unittest.mock import Mock, patch

import pytest

from data.states.game_state import GameState
from data.states.round_state import RoundPhase, RoundState
from data.types.base_types import DeckState
from data.types.pot_types import PotState
from tests.mocks.mock_agent import MockAgent
from tests.mocks.mock_betting import MockBetting
from tests.mocks.mock_deck import MockDeck
from tests.mocks.mock_hand import MockHand
from tests.mocks.mock_llm_client import MockLLMClient
from tests.mocks.mock_llm_response_generator import MockLLMResponseGenerator
from tests.mocks.mock_player import MockPlayer
from tests.mocks.mock_player_queue import MockPlayerQueue
from tests.mocks.mock_pot_manager import MockPotManager
from tests.mocks.mock_strategy_planner import MockStrategyPlanner


@pytest.fixture
def mock_agent():
    """Create a basic mock agent for testing."""
    agent = MockAgent(
        name="TestAgent", chips=1000, strategy_style="Aggressive", use_planning=True
    )
    return agent


@pytest.fixture
def mock_agents():
    """Create a list of mock agents with different configurations."""
    return [
        MockAgent("Alice", 1000, "Aggressive", use_planning=True),
        MockAgent("Bob", 1000, "Conservative", use_planning=True),
        MockAgent("Charlie", 1000, "Balanced", use_planning=False),
    ]


@pytest.fixture
def mock_betting():
    """Create a mock betting manager."""
    betting = MockBetting()
    betting.set_betting_round_result(
        pot_amount=100, side_pots=None, should_continue=True
    )
    return betting


@pytest.fixture
def mock_deck():
    """Create a mock deck with predefined behavior."""
    deck = MockDeck()
    return deck


@pytest.fixture
def mock_hand():
    """Create a mock hand for testing."""
    hand = MockHand()
    return hand


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client with default responses."""
    client = MockLLMClient()
    return client


@pytest.fixture
def mock_llm_response_generator():
    """Create a mock LLM response generator."""
    generator = MockLLMResponseGenerator()
    return generator


@pytest.fixture
def mock_player():
    """Create a basic mock player."""
    player = MockPlayer(name="TestPlayer", chips=1000)
    return player


@pytest.fixture
def mock_players():
    """Create a list of mock players."""
    return [
        MockPlayer("Player1", 1000),
        MockPlayer("Player2", 1000),
        MockPlayer("Player3", 1000),
    ]


@pytest.fixture
def mock_player_queue(mock_players):
    """Create a mock player queue with the mock players."""
    return MockPlayerQueue(mock_players)


@pytest.fixture
def mock_pot_manager():
    """Create a mock pot manager."""
    return MockPotManager()


@pytest.fixture
def mock_strategy_planner():
    """Create a mock strategy planner."""
    return MockStrategyPlanner(strategy_style="Aggressive")


@pytest.fixture
def mock_game_state(mock_players):
    """Create a mock game state for testing."""
    return GameState(
        players=[player.get_state() for player in mock_players],
        dealer_position=0,
        small_blind=10,
        big_blind=20,
        ante=0,
        min_bet=20,
        round_state=RoundState(
            round_number=1, phase=RoundPhase.PRE_DRAW, current_bet=20, raise_count=0
        ),
        pot_state=PotState(main_pot=0),
        deck_state=DeckState(cards_remaining=52),
    )


@pytest.fixture
def mock_game(mock_players, mock_pot_manager, mock_deck):
    """Create a mock game instance with common components."""
    game = Mock()
    game.players = mock_players
    game.pot_manager = mock_pot_manager
    game.deck = mock_deck
    game.round_state = RoundState(
        round_number=1, phase=RoundPhase.PRE_DRAW, current_bet=20, raise_count=0
    )
    game.config = Mock(small_blind=10, big_blind=20, ante=0, min_bet=20)
    return game


@pytest.fixture(autouse=True)
def setup_test_env():
    """Automatically set up test environment for all tests."""
    # Set environment variables
    with patch.dict(
        "os.environ", {"PYTEST_RUNNING": "1", "OPENAI_API_KEY": "test-key"}
    ):
        yield


@pytest.fixture(autouse=True)
def setup_logging():
    """Automatically configure logging for all tests."""
    import logging

    logging.basicConfig(level=logging.DEBUG)
    yield
    logging.basicConfig(level=logging.WARNING)
