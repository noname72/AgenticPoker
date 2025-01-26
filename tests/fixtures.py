"""Standard pytest fixtures for testing poker game components.

This module provides reusable pytest fixtures for testing the poker game implementation.
The fixtures create mock objects and test configurations that can be used across test files.

Fixture Categories:

1. Player Management:
    - mock_player: Basic player instance
    - mock_players: List of standard players
    - mock_active_players: Non-folded, non-all-in players
    - mock_big_blind_player: Player in big blind position
    - mock_all_in_player: Player who has gone all-in
    - mock_last_raiser: Player who made the last raise
    - mock_player_with_action: Player with pre-configured action

2. Game State:
    - mock_game_state: Complete game state configuration
    - mock_game: Full game instance with components
    - mock_round_state: Current round state
    - mock_config: Game configuration settings
    - game_state: Standard game state with positions

3. Betting Components:
    - mock_betting_state: Complete betting round state
    - mock_betting_round: Betting round functionality
    - mock_betting_logger: Logging for betting actions
    - mock_pot: Pot management
    - mock_pot_with_side_pots: Side pot configurations
    - mock_side_pot: Side pot factory

4. Draw Components:
    - mock_draw: Draw phase handler with configurable behaviors
    - mock_deck: Card deck with configurable dealing/shuffling
    - mock_hand: Player hand with configurable rankings

5. Table Management:
    - mock_table: Turn management table
    - mock_needs_to_act: Players pending actions
    - mock_acted_since_last_raise: Post-raise tracking

6. AI/Strategy Components:
    - mock_agent: AI player with configurable behaviors
    - mock_agents: List of AI players with different styles
    - mock_memory_store: Agent memory management
    - mock_strategy_planner: AI decision making
    - mock_llm_client: Language model integration
    - mock_llm_response_generator: AI response generation

7. Utility Fixtures:
    - setup_test_env: Environment configuration (auto-use)
    - setup_logging: Logging configuration (auto-use)
    - temp_dir: Temporary file storage
    - sample_cards: Standard test cards
    - mock_logger: Test logging capture
    - mock_websocket: Real-time communication
    - mock_database: Test database connection
    - mock_file_system: Test file system structure

Usage:
    These fixtures are automatically available to all test files through conftest.py.
    Simply declare the fixture name as a test parameter to use it:

    def test_betting_round(mock_betting_state, mock_table):
        # Access pre-configured betting state
        active_players = mock_betting_state["active_players"]
        
        # Use table for turn management
        next_player = mock_table.get_next_player()
        assert next_player in active_players

    def test_draw_phase(mock_draw, mock_game, mock_player):
        # Configure draw behavior
        mock_draw.set_discard_decision(
            player_name=mock_player.name,
            discard_indices=[0, 1]
        )
        mock_draw.handle_draw_phase(mock_game)

Auto-use Fixtures:
    - setup_test_env: Configures environment variables
    - setup_logging: Sets up test logging

Examples:
    # Test player action
    def test_player_decision(mock_player_with_action):
        action = mock_player_with_action.decide_action()
        assert action.action_type in [ActionType.CALL, ActionType.FOLD]

    # Test betting round
    def test_betting_execution(mock_betting_round, mock_players):
        pot_amount = mock_betting_round()
        assert pot_amount == 150

    # Test draw phase
    def test_discard_and_draw(mock_draw, mock_deck, mock_player):
        mock_draw.set_draw_outcome(
            player_name=mock_player.name,
            new_cards=sample_cards[:2]
        )
        mock_draw.process_discard_and_draw(mock_player, mock_deck, [0, 1])

Notes:
    - All fixtures are function-scoped by default
    - Mock objects are configured with reasonable defaults
    - Fixtures can be customized for specific test needs
    - Auto-use fixtures run automatically
    - Temporary resources are cleaned up after tests
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from data.states.game_state import GameState
from data.states.round_state import RoundPhase, RoundState
from data.types.action_decision import ActionType
from data.types.base_types import DeckState
from data.types.pot_types import PotState, SidePot
from tests.mocks.mock_agent import MockAgent
from tests.mocks.mock_betting import MockBetting
from tests.mocks.mock_deck import MockDeck
from tests.mocks.mock_hand import MockHand
from tests.mocks.mock_llm_client import MockLLMClient
from tests.mocks.mock_llm_response_generator import MockLLMResponseGenerator
from tests.mocks.mock_player import MockPlayer
from tests.mocks.mock_pot import MockPot
from tests.mocks.mock_strategy_planner import MockStrategyPlanner
from tests.mocks.mock_table import MockTable


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
    """Create a mock betting manager.

    Provides a MockBetting instance that mocks the three main functions from betting.py:
    - handle_betting_round: Returns whether betting should continue
    - betting_round: Processes a complete round of betting
    - collect_blinds_and_antes: Handles forced bets at start of hand

    Example:
        def test_betting(mock_betting):
            mock_betting.set_betting_round_result(should_continue=True)
            result = mock_betting.handle_betting_round(mock_game)
            assert result is True

    Returns:
        MockBetting: Configured betting manager for testing
    """
    betting = MockBetting()
    betting.set_betting_round_result(should_continue=True)
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
def player_factory():
    """Create a factory function for generating players with different states.

    This factory allows creating players with customized:
    - Name and chips
    - All-in status
    - Big blind status
    - Folded status
    - Bet amount
    - Action responses

    Example:
        def test_player_states(player_factory):
            all_in = player_factory(
                name="AllIn",
                chips=0,
                is_all_in=True,
                bet=1000
            )
            assert all_in.is_all_in
            assert all_in.chips == 0

            big_blind = player_factory(
                name="BigBlind",
                is_big_blind=True
            )
            assert big_blind.is_big_blind

            custom = player_factory(
                name="Custom",
                chips=500,
                action_response=ActionType.RAISE
            )
            assert custom.decide_action().action_type == ActionType.RAISE

    Args:
        name (str, optional): Player name. Defaults to "Player".
        chips (int, optional): Starting chips. Defaults to 1000.
        is_all_in (bool, optional): All-in status. Defaults to False.
        is_big_blind (bool, optional): Big blind status. Defaults to False.
        folded (bool, optional): Folded status. Defaults to False.
        bet (int, optional): Current bet amount. Defaults to 0.
        action_response (ActionType, optional): Pre-configured action response.
            Defaults to None.

    Returns:
        Callable: Factory function that creates MockPlayer instances
    """

    def _create_player(
        name="Player",
        chips=1000,
        is_all_in=False,
        is_big_blind=False,
        folded=False,
        bet=0,
        action_response=None,
    ):
        player = MockPlayer(name=name, chips=chips)
        player.is_all_in = is_all_in
        player.is_big_blind = is_big_blind
        player.folded = folded
        player.bet = bet

        if action_response:
            response = MagicMock()
            response.action_type = action_response
            response.raise_amount = 0
            player.decide_action = MagicMock(return_value=response)

        return player

    return _create_player


@pytest.fixture
def mock_players(player_factory):
    """Create a list of mock players for testing.

    Creates three players with standard configurations using player_factory.

    Example:
        def test_player_setup(mock_players):
            assert len(mock_players) == 3
            assert mock_players[0].name == "Player1"
            assert all(p.chips == 1000 for p in mock_players)

    Returns:
        List[MockPlayer]: List of three configured mock players
    """
    return [player_factory(name=f"Player{i+1}") for i in range(3)]


@pytest.fixture
def mock_table(mock_players):
    """Create a mock table with pre-configured players and betting state.

    This fixture provides a MockTable instance that matches the real Table's
    functionality, including:
    - Player state tracking (active, all-in, folded)
    - Betting action tracking (needs_to_act, acted_since_last_raise)
    - Turn management
    - Round completion checks

    Args:
        mock_players: List of mock players to initialize the table

    Returns:
        MockTable: Configured table instance with default behaviors
    """
    table = MockTable(mock_players)

    # Initialize with default state
    table.needs_to_act = set(mock_players)
    table.acted_since_last_raise = set()

    # Update player state lists
    table._update_player_lists()  # This now includes chips > 0 check

    # Configure default mock behaviors
    table.is_round_complete.return_value = False
    table.get_next_player.side_effect = table._default_get_next_player
    table.all_players_acted.return_value = False

    return table


@pytest.fixture
def mock_pot():
    """Create a mock pot manager for testing pot operations.

    Provides a clean MockPot instance for tracking:
    - Main pot amounts
    - Side pot calculations
    - Player pot eligibility

    Example:
        def test_pot_management(mock_pot):
            mock_pot.add_to_pot(100)
            mock_pot.create_side_pot(50, ["Player1"])
            assert mock_pot.get_total_pot() == 150

    Returns:
        MockPot: Fresh pot instance
    """
    return MockPot()


@pytest.fixture
def mock_strategy_planner():
    """Create a mock strategy planner with aggressive default style.

    Configures a strategy planner for testing AI decision making with:
    - Aggressive play style
    - Default strategy parameters
    - Pre-configured decision making patterns

    Example:
        def test_strategy_planning(mock_strategy_planner):
            decision = mock_strategy_planner.plan_action(game_state)
            assert decision.style == "Aggressive"

    Returns:
        MockStrategyPlanner: Configured strategy planner
    """
    return MockStrategyPlanner(strategy_style="Aggressive")


@pytest.fixture
def mock_game_state(mock_players):
    """Create a mock game state with standard testing configuration.

    Initializes a GameState with:
    - List of player states
    - Dealer at position 0
    - Standard blind structure (10/20)
    - Pre-draw phase
    - Empty pot
    - Full deck

    Example:
        def test_game_state(mock_game_state):
            assert mock_game_state.dealer_position == 0
            assert mock_game_state.small_blind == 10
            assert mock_game_state.round_state.phase == RoundPhase.PRE_DRAW

    Returns:
        GameState: Configured game state for testing
    """
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
def mock_game(mock_players, mock_pot, mock_deck):
    """Create a complete mock game instance with standard components.

    Configures a game instance with:
    - List of players
    - Pot manager
    - Deck
    - Standard betting config (10/20 blinds)

    Example:
        def test_game_setup(mock_game):
            assert len(mock_game.table) == 3
            assert mock_game.round_state.phase == RoundPhase.PRE_DRAW
            assert mock_game.config.small_blind == 10

    Returns:
        Mock: Configured game instance with all necessary components
    """
    game = Mock()
    game.table = mock_players
    game.pot = mock_pot
    game.deck = mock_deck
    game.round_state = RoundState(
        round_number=1, phase=RoundPhase.PRE_DRAW, current_bet=20, raise_count=0
    )
    game.config = Mock(small_blind=10, big_blind=20, ante=0, min_bet=20)
    return game


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up the test environment with required configuration.

    Automatically configures:
    - PYTEST_RUNNING environment variable
    - OpenAI API test key

    This fixture runs automatically for all tests.

    Example:
        # No explicit usage needed - runs automatically
        def test_something():
            assert os.environ["PYTEST_RUNNING"] == "1"
            assert os.environ["OPENAI_API_KEY"] == "test-key"
    """
    with patch.dict(
        "os.environ", {"PYTEST_RUNNING": "1", "OPENAI_API_KEY": "test-key"}
    ):
        yield


@pytest.fixture(autouse=True)
def setup_logging():
    """Configure logging for test execution.

    Sets up:
    - Debug level logging during tests
    - Resets to warning level after tests

    This fixture runs automatically for all tests.

    Example:
        # No explicit usage needed - runs automatically
        def test_with_logging():
            logging.debug("This will be captured")
            # Logging level resets after test
    """
    import logging

    logging.basicConfig(level=logging.DEBUG)
    yield
    logging.basicConfig(level=logging.WARNING)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test file operations.

    Features:
    - Creates unique temporary directory
    - Automatically cleans up after test
    - Safe for parallel test execution

    Example:
        def test_file_operations(temp_dir):
            file_path = os.path.join(temp_dir, "test.txt")
            with open(file_path, "w") as f:
                f.write("test data")
            assert os.path.exists(file_path)
            # Directory and contents auto-cleanup after test

    Returns:
        str: Path to temporary directory
    """
    import shutil
    import tempfile

    test_dir = tempfile.mkdtemp()
    yield test_dir
    shutil.rmtree(test_dir)


@pytest.fixture
def sample_cards():
    """Provide a standard set of test cards (Royal Flush in Spades).

    Creates a list of cards:
    - Ace of Spades
    - King of Spades
    - Queen of Spades
    - Jack of Spades
    - Ten of Spades

    Example:
        def test_hand_evaluation(sample_cards):
            hand = Hand(sample_cards)
            assert hand.is_royal_flush()
            assert all(card.suit == "♠" for card in sample_cards)

    Returns:
        List[Card]: Five cards forming a royal flush in spades
    """
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
    """Create a mock memory store for testing agent memory management.

    Provides a simple in-memory store with methods for:
    - Adding memories with metadata
    - Retrieving relevant memories
    - Clearing memory state

    Example:
        def test_memory_storage(mock_memory_store):
            mock_memory_store.add_memory("Player1 raised", {"round": 1})
            memories = mock_memory_store.get_relevant_memories("raise")
            assert len(memories) == 1
            assert memories[0]["text"] == "Player1 raised"

    Returns:
        MockMemoryStore: Memory store instance with basic memory operations
    """

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
    round_state.phase = RoundPhase.PRE_DRAW
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
    """Create a factory for mock side pots with configurable amounts and players.

    Provides a function to create SidePot instances with:
    - Configurable pot amount (default: 50)
    - List of eligible players (default: ["Player1"])

    Example:
        def test_side_pot_creation(mock_side_pot):
            # Create basic side pot
            pot1 = mock_side_pot()
            assert pot1.amount == 50

            # Create custom side pot
            pot2 = mock_side_pot(amount=100, players=["Player1", "Player2"])
            assert len(pot2.eligible_players) == 2

    Returns:
        Callable: Factory function for creating SidePot instances
    """

    def _create_side_pot(amount=50, players=None):
        if players is None:
            players = ["Player1"]
        return SidePot(amount=amount, eligible_players=players)

    return _create_side_pot


@pytest.fixture
def mock_betting_round():
    """Create a mock of the betting_round function.

    Patches the betting_round function to:
    - Process a complete round of betting
    - Allow verification of betting round calls
    - Support error simulation if needed

    Example:
        def test_betting_execution(mock_betting_round, mock_game):
            mock_betting_round(mock_game)
            mock_betting_round.assert_called_once_with(mock_game)

    Returns:
        MagicMock: Configured mock of the betting_round function
    """
    with patch("game.betting.betting_round") as mock:
        yield mock


@pytest.fixture
def mock_active_players(mock_players):
    """Create a list of active (non-folded, non-all-in, with chips) players.

    Configures each player with:
    - folded = False
    - is_all_in = False
    - bet = 0
    - chips = 1000 (ensuring they have chips to play)

    Then filters to return only truly active players (not folded, not all-in, has chips).

    Example:
        def test_active_player_count(mock_active_players):
            assert len(mock_active_players) == 3
            assert all(
                not p.folded and not p.is_all_in and p.chips > 0
                for p in mock_active_players
            )

    Returns:
        List[MockPlayer]: List of active players ready for testing
    """
    for player in mock_players:
        player.folded = False
        player.is_all_in = False
        player.bet = 0
        player.chips = 1000
    return [p for p in mock_players if not p.folded and not p.is_all_in and p.chips > 0]


@pytest.fixture
def mock_needs_to_act(mock_active_players):
    """Create a set of players that need to act in the current betting round.

    Initially includes all active players (not folded, not all-in).
    Used to track which players still need to take their turn.

    Example:
        def test_betting_tracking(mock_needs_to_act, mock_player):
            assert mock_player in mock_needs_to_act
            mock_needs_to_act.discard(mock_player)
            assert mock_player not in mock_needs_to_act

    Returns:
        Set[MockPlayer]: Set of players who need to act
    """
    return set(mock_active_players)


@pytest.fixture
def mock_acted_since_last_raise():
    """Create an empty set for tracking players who have acted since the last raise.

    This set is used to determine when a betting round is complete.
    It gets cleared when:
    - A new betting round starts
    - A player makes a raise

    Example:
        def test_raise_tracking(mock_acted_since_last_raise, mock_player):
            assert len(mock_acted_since_last_raise) == 0
            mock_acted_since_last_raise.add(mock_player)
            assert mock_player in mock_acted_since_last_raise

    Returns:
        Set[MockPlayer]: Empty set for tracking post-raise actions
    """
    return set()


@pytest.fixture
def mock_last_raiser(mock_player):
    """Create a mock player representing the last player to raise.

    Configures a player with:
    - Name set to "LastRaiser"
    - Standard player attributes
    - Identifiable for testing raise tracking

    Example:
        def test_raise_tracking(mock_last_raiser, mock_betting_state):
            assert mock_betting_state["last_raiser"].name == "LastRaiser"
            assert mock_last_raiser in mock_betting_state["acted_since_last_raise"]

    Returns:
        MockPlayer: Player configured as the last raiser
    """
    mock_player.name = "LastRaiser"
    return mock_player


@pytest.fixture
def mock_big_blind_player(mock_player):
    """Create a mock player in the big blind position.

    Configures a player with:
    - is_big_blind flag set to True
    - Name set to "BigBlind"
    - Standard player attributes

    Example:
        def test_big_blind_action(mock_big_blind_player):
            assert mock_big_blind_player.is_big_blind
            assert mock_big_blind_player.name == "BigBlind"

    Returns:
        MockPlayer: Player configured as the big blind
    """
    mock_player.is_big_blind = True
    mock_player.name = "BigBlind"
    return mock_player


@pytest.fixture
def mock_all_in_player(mock_player):
    """Create a mock player who has gone all-in.

    Configures a player with:
    - is_all_in flag set to True
    - No remaining chips (chips = 0)
    - Full bet amount (bet = 1000)
    - Name set to "AllInPlayer"

    Example:
        def test_all_in_state(mock_all_in_player):
            assert mock_all_in_player.is_all_in
            assert mock_all_in_player.chips == 0
            assert mock_all_in_player.bet == 1000

    Returns:
        MockPlayer: Player configured in all-in state
    """
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
    mock_table,
):
    """Create a complete betting state for testing betting rounds.

    Provides a dictionary containing all components needed for testing betting:
    - game: Mock game instance
    - active_players: List of players who can act
    - needs_to_act: Set of players who haven't acted
    - acted_since_last_raise: Set of players who acted since last raise
    - last_raiser: Player who made the last raise
    - table: Mock table managing player order

    Example:
        def test_betting_state(mock_betting_state):
            assert len(mock_betting_state["active_players"]) > 0
            assert mock_betting_state["last_raiser"] is not None

    Returns:
        dict: Complete betting state configuration
    """
    # Configure table with betting state
    mock_table.needs_to_act = mock_needs_to_act
    mock_table.acted_since_last_raise = mock_acted_since_last_raise
    mock_table.last_raiser = mock_last_raiser

    # Update active players list (not folded, not all-in, has chips)
    mock_table.active_players = [
        p
        for p in mock_active_players
        if not p.folded and not p.is_all_in and p.chips > 0
    ]

    return {
        "game": mock_game,
        "active_players": mock_active_players,
        "needs_to_act": mock_needs_to_act,
        "acted_since_last_raise": mock_acted_since_last_raise,
        "last_raiser": mock_last_raiser,
        "table": mock_table,
    }


@pytest.fixture
def mock_player_with_action(mock_player, mock_action_response):
    """Create a mock player with pre-configured action response.

    Sets up a player with:
    - Predetermined action response
    - Mocked execute method
    - Ready for action verification

    Example:
        def test_player_action(mock_player_with_action):
            action = mock_player_with_action.decide_action()
            assert action == mock_action_response
            mock_player_with_action.execute.assert_not_called()

    Returns:
        MockPlayer: Player configured with predetermined action
    """
    mock_player.decide_action.return_value = mock_action_response
    mock_player.execute = MagicMock()
    return mock_player


@pytest.fixture
def mock_pot_with_side_pots(mock_pot, mock_side_pot):
    """Create a mock pot with pre-configured side pots.

    Sets up a pot manager with:
    - Two default side pots (50 and 100 chips)
    - Different eligible players for each pot
    - Configured side pot calculation results

    Example:
        def test_side_pot_management(mock_pot_with_side_pots):
            side_pots = mock_pot_with_side_pots.side_pots
            assert len(side_pots) == 2
            assert side_pots[0]["amount"] == 50
            assert side_pots[1]["amount"] == 100

    Returns:
        MockPot: Pot configured with side pots
    """
    side_pots = [mock_side_pot(50, ["Player1"]), mock_side_pot(100, ["Player2"])]
    mock_pot.calculate_side_pots.return_value = side_pots
    mock_pot.side_pots = [
        {"amount": pot.amount, "eligible_players": pot.eligible_players}
        for pot in side_pots
    ]
    return mock_pot


@pytest.fixture
def mock_blind_config():
    """Create a standard blind/ante configuration for testing.

    Returns a tuple of (dealer_index, small_blind, big_blind, ante) with common
    defaults used in tests:
    - dealer_index: 0 (first player is dealer)
    - small_blind: 50 chips
    - big_blind: 100 chips
    - ante: 10 chips

    Example:
        def test_collect_blinds(mock_blind_config, mock_players):
            dealer_index, small_blind, big_blind, ante = mock_blind_config
            collected = collect_blinds_and_antes(
                mock_players, dealer_index, small_blind, big_blind, ante, mock_game
            )
            assert collected == small_blind + big_blind + (ante * len(mock_players))

    Returns:
        Tuple[int, int, int, int]: (dealer_index, small_blind, big_blind, ante)
    """
    return (0, 50, 100, 10)


@pytest.fixture
def mock_insufficient_chips_players(player_factory):
    """Create a list of players with intentionally low chip counts.

    Creates three players with different chip amounts using player_factory:
    - Player1: 1000 chips (normal stack)
    - Player2: 30 chips (not enough for small blind of 50)
    - Player3: 60 chips (not enough for big blind of 100)

    Example:
        def test_partial_blinds(mock_insufficient_chips_players, mock_game):
            collected = collect_blinds_and_antes(
                mock_insufficient_chips_players, 0, 50, 100, 0, mock_game
            )
            assert collected == 90  # 30 (partial SB) + 60 (partial BB)

    Returns:
        List[MockPlayer]: Three players with configured chip stacks
    """
    return [
        player_factory(name="Player1", chips=1000),
        player_factory(name="Player2", chips=30),
        player_factory(name="Player3", chips=60),
    ]


@pytest.fixture
def game_state(mock_players):
    """Create a standard game state for testing.

    Creates a GameState instance with:
    - 4 players with standard positions (dealer, SB, BB, UTG)
    - Standard blinds (50/100)
    - Standard ante (10)
    - Pre-draw phase
    - Empty pot
    - Full deck
    - Default raise limits
    """
    from data.states.game_state import GameState
    from data.states.player_state import PlayerState
    from data.states.round_state import RoundPhase, RoundState
    from data.types.base_types import DeckState
    from data.types.player_types import PlayerPosition
    from data.types.pot_types import PotState

    # Create player states with proper positions
    player_states = [
        PlayerState(
            name=player.name,
            chips=player.chips,
            bet=player.bet,
            position=(
                PlayerPosition.DEALER if i == 0
                else PlayerPosition.SMALL_BLIND if i == 1
                else PlayerPosition.BIG_BLIND if i == 2
                else PlayerPosition.UNDER_THE_GUN
            ),
            folded=player.folded,
            is_all_in=False,
            checked=False,
            called=False,
        )
        for i, player in enumerate(mock_players)
    ]

    # Create round state with proper initialization
    round_state = RoundState(
        round_number=1,
        phase=RoundPhase.PRE_DRAW,
        current_bet=100,
        raise_count=0,
        dealer_position=0,
        small_blind_position=1,
        big_blind_position=2,
        first_bettor_index=3,
        main_pot=0,
        side_pots=[],
    )

    return GameState(
        players=player_states,
        dealer_position=0,
        small_blind=50,
        big_blind=100,
        ante=10,
        min_bet=100,
        round_state=round_state,
        pot_state=PotState(main_pot=0),
        deck_state=DeckState(cards_remaining=52),
        active_player_position=None,
        max_raise_multiplier=3,
        max_raises_per_round=4,
    )


@pytest.fixture
def mock_draw():
    """Create a mock draw handler for testing draw phase functionality.

    This fixture provides a MockDraw instance with:
    - Default draw phase behaviors
    - Configurable discard decisions
    - Configurable draw outcomes
    - Proper logging through DrawLogger
    - Error simulation capabilities

    Usage:
        def test_draw_phase(mock_draw, mock_game, mock_player):
            # Configure specific discard decision
            mock_draw.set_discard_decision(
                player_name=mock_player.name,
                discard_indices=[0, 1]
            )

            # Configure cards to be drawn
            mock_draw.set_draw_outcome(
                player_name=mock_player.name,
                new_cards=[Card("A", "♠"), Card("K", "♠")]
            )

            # Execute draw phase
            mock_draw.handle_draw_phase(mock_game)

            # Verify behavior
            mock_draw.get_discard_indices.assert_called_with(mock_player)
            mock_draw.process_discard_and_draw.assert_called_once()

    Returns:
        MockDraw: Configured draw handler for testing
    """
    from tests.mocks.mock_draw import MockDraw

    return MockDraw()
