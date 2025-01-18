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
    Game Components:
        mock_agent: A basic MockAgent instance with default configuration
        mock_agents: List of MockAgents with different strategies
        mock_betting: MockBetting instance with pre-configured betting results
        mock_deck: MockDeck instance for simulating card dealing
        mock_hand: MockHand instance for testing hand evaluation
        mock_player: Basic MockPlayer instance
        mock_players: List of MockPlayers for testing multiplayer scenarios
        mock_player_queue: MockPlayerQueue configured with mock_players
        mock_pot_manager: MockPotManager for testing pot management
        mock_game_state: GameState instance with default test configuration
        mock_game: Mock game instance with common components configured
        mock_config: Game configuration with standard settings
        mock_hand_evaluator: Hand evaluation with default royal flush result
        
    AI/LLM Components:
        mock_llm_client: MockLLMClient for testing AI interactions
        mock_llm_response_generator: MockLLMResponseGenerator for testing AI responses
        mock_strategy_planner: MockStrategyPlanner with aggressive strategy
        mock_openai: OpenAI API mock with configurable responses
        mock_memory_store: Memory store for testing agent memory/history
        
    Utility Fixtures:
        temp_dir: Temporary directory that auto-cleans after tests
        sample_cards: Standard set of test cards (royal flush in spades)
        mock_logger: Logger with captured output for testing logs
        mock_session: Game session ID generator
        mock_file_system: File system with standard directories
        mock_database: SQLite database for testing
        mock_websocket: WebSocket mock for testing real-time communication

Auto-use Fixtures:
    setup_test_env: Configures environment variables for testing
    setup_logging: Configures logging for test execution

Examples:
    # Test agent decision making
    def test_agent_makes_valid_decision(mock_agent, mock_game_state):
        action = mock_agent.decide_action(mock_game_state)
        assert action.action_type in [ActionType.CALL, ActionType.FOLD, ActionType.RAISE]

    # Test betting round
    def test_betting_round(mock_betting, mock_players, mock_game):
        pot, side_pots, continue_game = mock_betting.handle_betting_round(mock_game)
        assert isinstance(pot, int)
        assert pot >= 0

    # Test file operations
    def test_save_game_log(mock_file_system, mock_logger):
        logger, log_stream = mock_logger
        logger.info("Game started")
        assert "Game started" in log_stream.getvalue()

    # Test database operations
    def test_store_game_result(mock_database):
        cursor = mock_database.cursor()
        cursor.execute("CREATE TABLE games (id TEXT, winner TEXT)")
        cursor.execute("INSERT INTO games VALUES (?, ?)", ("game1", "Player1"))
        mock_database.commit()
        
        result = cursor.execute("SELECT winner FROM games WHERE id=?", ("game1",)).fetchone()
        assert result[0] == "Player1"

Note:
    - All fixtures are function-scoped by default
    - Auto-use fixtures run automatically for all tests
    - Mock objects are configured with reasonable defaults but can be customized
    - Use fixture factories when you need parameterized fixtures
    - Utility fixtures handle cleanup automatically
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from data.states.game_state import GameState
from data.states.round_state import RoundPhase, RoundState
from data.types.action_response import ActionType
from data.types.base_types import DeckState
from data.types.pot_types import PotState, SidePot
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
    queue = MockPlayerQueue(mock_players)
    queue.is_round_complete.side_effect = [False, False, True]  # Default behavior
    queue.get_next_player.side_effect = mock_players  # Return players in order
    return queue


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


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files.

    Automatically cleans up after tests.
    """
    import shutil
    import tempfile

    test_dir = tempfile.mkdtemp()
    yield test_dir
    shutil.rmtree(test_dir)


@pytest.fixture
def sample_cards():
    """Provide a standard set of test cards."""
    from game.card import Card

    return [
        Card("A", "♠"),
        Card("K", "♠"),
        Card("Q", "♠"),
        Card("J", "♠"),
        Card("10", "♠"),
    ]


@pytest.fixture
def mock_memory_store():
    """Create a mock memory store for testing."""

    class MockMemoryStore:
        def __init__(self):
            self.memories = []

        def add_memory(self, text, metadata=None):
            self.memories.append({"text": text, "metadata": metadata or {}})

        def get_relevant_memories(self, query, k=3):
            return self.memories[:k]

        def clear(self):
            self.memories = []

        def close(self):
            pass

    return MockMemoryStore()


@pytest.fixture
def mock_config():
    """Create a mock game configuration."""
    from unittest.mock import MagicMock

    config = MagicMock()
    config.starting_chips = 1000
    config.small_blind = 10
    config.big_blind = 20
    config.ante = 0
    config.min_bet = 20
    config.max_raise_multiplier = 3
    config.max_raises_per_round = 4
    return config


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    import logging

    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)

    # Create string buffer handler to capture log output
    from io import StringIO

    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    yield logger, log_stream

    # Cleanup
    logger.removeHandler(handler)
    log_stream.close()


@pytest.fixture
def mock_openai():
    """Mock OpenAI API responses."""
    from unittest.mock import MagicMock

    from openai.types.chat import ChatCompletion, ChatCompletionMessage
    from openai.types.chat.chat_completion import Choice

    mock_client = MagicMock()

    def create_response(content="Test response"):
        return ChatCompletion(
            id="test_id",
            model="gpt-3.5-turbo",
            object="chat.completion",
            created=1234567890,
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content=content,
                        role="assistant",
                    ),
                )
            ],
            usage={"total_tokens": 100, "prompt_tokens": 50, "completion_tokens": 50},
        )

    mock_client.chat.completions.create.side_effect = create_response
    return mock_client


@pytest.fixture
def mock_session():
    """Create a mock game session."""
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d_%H%M%S")


@pytest.fixture
def mock_hand_evaluator():
    """Create a mock hand evaluator."""
    from unittest.mock import MagicMock

    evaluator = MagicMock()

    def evaluate(cards):
        return (5, [14, 13, 12, 11, 10], "Royal Flush")  # Default to royal flush

    evaluator.evaluate = evaluate
    return evaluator


@pytest.fixture
def mock_file_system(temp_dir):
    """Set up a mock file system with required directories."""
    import os

    # Create standard directories
    dirs = ["results", "logs", "data"]
    for dir_name in dirs:
        os.makedirs(os.path.join(temp_dir, dir_name), exist_ok=True)

    return temp_dir


@pytest.fixture
def mock_database(temp_dir):
    """Create a temporary test database."""
    import os
    import sqlite3

    db_path = os.path.join(temp_dir, "test.db")
    conn = sqlite3.connect(db_path)

    yield conn

    conn.close()
    os.remove(db_path)


@pytest.fixture
def mock_websocket():
    """Create a mock websocket for testing real-time communication."""
    from unittest.mock import MagicMock

    ws = MagicMock()
    ws.send = MagicMock()
    ws.receive = MagicMock(return_value='{"type": "test"}')
    ws.close = MagicMock()

    return ws


@pytest.fixture
def mock_betting_logger():
    """Create a mock betting logger."""
    with patch("game.betting.BettingLogger") as mock_logger:
        mock_logger.log_collecting_antes = MagicMock()
        mock_logger.log_blind_or_ante = MagicMock()
        mock_logger.log_player_turn = MagicMock()
        mock_logger.log_line_break = MagicMock()
        mock_logger.log_skip_player = MagicMock()
        yield mock_logger


@pytest.fixture
def mock_round_state():
    """Create a mock round state."""
    round_state = MagicMock()
    round_state.phase = RoundPhase.PREFLOP
    round_state.big_blind_position = 1
    round_state.current_bet = 0
    round_state.raise_count = 0
    return round_state


@pytest.fixture
def mock_action_response():
    """Create a mock action response."""
    response = MagicMock()
    response.action_type = ActionType.CALL
    response.raise_amount = 0
    return response


@pytest.fixture
def mock_side_pot():
    """Create a mock side pot."""

    def _create_side_pot(amount=50, players=None):
        if players is None:
            players = ["Player1"]
        return SidePot(amount=amount, eligible_players=players)

    return _create_side_pot


@pytest.fixture
def mock_betting_round():
    """Create a mock betting round."""
    with patch("game.betting.betting_round") as mock:
        mock.return_value = 150  # Default pot amount
        yield mock


@pytest.fixture
def mock_active_players(mock_players):
    """Create a list of active (non-folded) players."""
    for player in mock_players:
        player.folded = False
        player.is_all_in = False
        player.bet = 0
        player.chips = 1000
    return mock_players


@pytest.fixture
def mock_needs_to_act(mock_active_players):
    """Create a set of players that need to act."""
    return set(mock_active_players)


@pytest.fixture
def mock_acted_since_last_raise():
    """Create an empty set for tracking players who acted since last raise."""
    return set()


@pytest.fixture
def mock_last_raiser(mock_player):
    """Create a mock last raiser."""
    mock_player.name = "LastRaiser"
    return mock_player


@pytest.fixture
def mock_big_blind_player(mock_player):
    """Create a mock big blind player."""
    mock_player.is_big_blind = True
    mock_player.name = "BigBlind"
    return mock_player


@pytest.fixture
def mock_all_in_player(mock_player):
    """Create a mock player who is all-in."""
    mock_player.is_all_in = True
    mock_player.bet = 1000
    mock_player.chips = 0
    mock_player.name = "AllInPlayer"
    return mock_player


@pytest.fixture
def mock_betting_state(
    mock_game,
    mock_active_players,
    mock_needs_to_act,
    mock_acted_since_last_raise,
    mock_last_raiser,
):
    """Create a complete betting state for testing."""
    return {
        "game": mock_game,
        "active_players": mock_active_players,
        "needs_to_act": mock_needs_to_act,
        "acted_since_last_raise": mock_acted_since_last_raise,
        "last_raiser": mock_last_raiser,
    }


@pytest.fixture
def mock_player_with_action(mock_player, mock_action_response):
    """Create a mock player with pre-configured action response."""
    mock_player.decide_action.return_value = mock_action_response
    mock_player.execute = MagicMock()
    return mock_player


@pytest.fixture
def mock_pot_with_side_pots(mock_pot_manager, mock_side_pot):
    """Create a mock pot manager with side pots configured."""
    side_pots = [mock_side_pot(50, ["Player1"]), mock_side_pot(100, ["Player2"])]
    mock_pot_manager.calculate_side_pots.return_value = side_pots
    mock_pot_manager.side_pots = [
        {"amount": pot.amount, "eligible_players": pot.eligible_players}
        for pot in side_pots
    ]
    return mock_pot_manager
