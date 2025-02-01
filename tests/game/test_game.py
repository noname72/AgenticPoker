from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest

from agents.agent import Agent
from data.types.action_decision import ActionType
from data.types.pot_types import SidePot
from game import AgenticPoker
from game.hand import Hand


@pytest.fixture
def mock_players():
    """Fixture to create mock players."""
    players = []
    for name in ["Alice", "Bob", "Charlie"]:
        player = Mock(spec=Agent)
        player.name = name
        player.chips = 1000
        player.folded = False
        player.bet = 0
        # Mock hand attribute
        player.hand = Mock(spec=Hand)
        player.hand.__eq__ = lambda self, other: False
        player.hand.__gt__ = lambda self, other: False

        # Create a proper place_bet method that updates chips
        def make_place_bet(p):
            def place_bet(amount):
                actual_amount = min(amount, p.chips)
                p.chips -= actual_amount
                p.bet += actual_amount
                return actual_amount

            return place_bet

        player.place_bet = make_place_bet(player)
        players.append(player)
    return players


@pytest.fixture
def game(mock_players):
    """Fixture to create game instance."""
    return AgenticPoker(
        players=mock_players,
        small_blind=50,
        big_blind=100,
        ante=10,
        session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
    )


def test_game_initialization(game, mock_players):
    """Test game initialization with valid parameters."""
    assert len(game.table) == 3
    assert game.small_blind == 50
    assert game.big_blind == 100
    assert game.ante == 10
    assert game.session_id is not None
    # Verify all players have initial chips
    for player in game.table:
        assert player.chips == 1000


def test_invalid_game_initialization(mock_players):
    """Test game initialization with invalid parameters."""
    with pytest.raises(ValueError):
        AgenticPoker(
            players=[],  # Empty players list
            small_blind=50,
            big_blind=100,
            ante=10,
        )

    with pytest.raises(ValueError):
        # Create players with negative chips
        invalid_players = [
            Mock(spec=Agent, chips=-1000, name=f"Player{i}") for i in range(3)
        ]
        AgenticPoker(
            players=invalid_players,
            small_blind=50,
            big_blind=100,
            ante=10,
        )


def test_dealer_rotation(game, mock_players):
    """Test dealer button rotation between rounds."""
    initial_dealer = game.dealer_index

    # Reset round which rotates dealer
    game._reset_round()

    # Verify dealer rotated
    expected_dealer = (initial_dealer + 1) % len(mock_players)
    assert game.dealer_index == expected_dealer


def test_round_initialization(game, mock_players):
    """Test initialization of a new round."""
    game._initialize_round()

    # Verify round state
    assert game.pot.pot == 0
    assert all(player.bet == 0 for player in game.table)
    assert all(not player.folded for player in game.table)
    assert all(hasattr(player, "hand") for player in game.table)


def test_collect_blinds_and_antes(game, player_factory):
    """Test that blinds and antes are collected correctly and pot is updated properly."""
    # Create players with known chip stacks
    players = [
        player_factory(name="Alice", chips=1000),
        player_factory(name="Bob", chips=1000),
        player_factory(name="Charlie", chips=1000),
    ]
    game.table.players = players

    # Set up initial state
    game.small_blind = 50
    game.big_blind = 100
    game.ante = 10
    game.dealer_index = 0

    # Store initial chip counts
    initial_chips = {p: p.chips for p in game.table}

    # Collect blinds and antes
    game._collect_blinds_and_antes()

    # Calculate expected pot amount
    num_players = len(players)
    expected_antes = num_players * game.ante  # 3 players * $10 = $30
    expected_blinds = game.small_blind + game.big_blind  # $50 + $100 = $150
    expected_pot = expected_antes + expected_blinds  # $30 + $150 = $180

    # Verify pot amount
    assert (
        game.pot.pot == expected_pot
    ), f"Expected pot of ${expected_pot}, got ${game.pot.pot}"

    # Verify player chip counts
    dealer = game.table[0]  # Alice
    sb_player = game.table[1]  # Bob
    bb_player = game.table[2]  # Charlie

    # Check dealer's chips (only pays ante)
    assert dealer.chips == initial_chips[dealer] - game.ante

    # Check small blind player's chips (pays ante + small blind)
    assert sb_player.chips == initial_chips[sb_player] - game.ante - game.small_blind

    # Check big blind player's chips (pays ante + big blind)
    assert bb_player.chips == initial_chips[bb_player] - game.ante - game.big_blind

    # Verify current bet is set to big blind
    assert game.current_bet == game.big_blind


def test_pot_not_double_counted(game, player_factory):
    """Test that pot amounts are correctly tracked during betting.

    This test verifies that:
    1. Bets are added to pot when placed
    2. Pot increases incrementally with each bet
    3. Final pot matches actual player contributions
    """
    # Create players with known chip stacks
    players = [
        player_factory(name="Alice", chips=1000),  # Dealer
        player_factory(name="Bob", chips=1000),  # Small Blind
        player_factory(name="Charlie", chips=1000),  # Big Blind
        player_factory(name="Randy", chips=1000),  # UTG
    ]
    game.table.players = players

    # Set up initial state
    game.small_blind = 50
    game.big_blind = 100
    game.ante = 10
    game.dealer_index = 0

    # Reset pot before collecting blinds
    game.pot.reset_pot()

    # Collect blinds and antes
    game._collect_blinds_and_antes()

    # Verify initial pot after blinds/antes
    # Each player pays 10 ante (40 total)
    # SB pays 50, BB pays 100
    expected_initial_pot = 40 + 50 + 100
    assert (
        game.pot.pot == expected_initial_pot
    ), f"Expected initial pot of ${expected_initial_pot}, got ${game.pot.pot}"

    # Simulate pre-draw betting round:
    # Alice raises to 300
    alice = players[0]
    alice.chips -= 300
    alice.bet += 300
    game.pot.add_to_pot(300)
    expected_pot = expected_initial_pot + 300
    assert (
        game.pot.pot == expected_pot
    ), f"Pot should be ${expected_pot} after Alice's bet"

    # Bob folds (already put in SB)
    bob = players[1]
    bob.folded = True

    # Charlie calls (already put in BB)
    charlie = players[2]
    charlie.chips -= 200  # Additional 200 to match 300 total
    charlie.bet += 200
    game.pot.add_to_pot(200)
    expected_pot = expected_pot + 200
    assert (
        game.pot.pot == expected_pot
    ), f"Pot should be ${expected_pot} after Charlie's bet"

    # Randy calls
    randy = players[3]
    randy.chips -= 300
    randy.bet += 300
    game.pot.add_to_pot(300)
    expected_pot = expected_pot + 300
    assert (
        game.pot.pot == expected_pot
    ), f"Pot should be ${expected_pot} after Randy's bet"

    # End betting round (should only clear bets, not modify pot)
    initial_pot = game.pot.pot
    game.pot.end_betting_round(game.table.players)
    assert game.pot.pot == initial_pot, "Pot should not change at end of betting round"

    # Verify player chip counts
    assert alice.chips == 1000 - 10 - 300, f"Alice's chips incorrect: {alice.chips}"
    assert bob.chips == 1000 - 10 - 50, f"Bob's chips incorrect: {bob.chips}"
    assert (
        charlie.chips == 1000 - 10 - 100 - 200
    ), f"Charlie's chips incorrect: {charlie.chips}"
    assert randy.chips == 1000 - 10 - 300, f"Randy's chips incorrect: {randy.chips}"


def test_post_draw_betting_skipped_all_all_in(game, player_factory):
    """Test that post-draw betting is skipped when all remaining players are all-in."""
    # Create players in all-in state
    all_in1 = player_factory(name="AllIn1", chips=0, is_all_in=True, bet=500)
    all_in2 = player_factory(name="AllIn2", chips=0, is_all_in=True, bet=300)
    folded = player_factory(name="Folded", folded=True)

    game.table.players = [all_in1, all_in2, folded]

    # Run post-draw betting
    result = game._handle_post_draw_phase()

    # Verify betting was skipped and returned True to continue to showdown
    assert result is True


def test_handle_player_eliminations_returns_false_one_player(game, player_factory):
    """Test that _handle_player_eliminations returns False when one player remains."""
    # Create players - one with chips, two without
    players = [
        player_factory(name="Alice", chips=1000),
        player_factory(name="Bob", chips=0),
        player_factory(name="Charlie", chips=0),
    ]
    game.table.players = players
    eliminated_players = []

    # Need to call twice - first call removes Bob and Charlie, second call checks table size
    first_result = game._handle_player_eliminations(eliminated_players)
    second_result = game._handle_player_eliminations(eliminated_players)

    # Verify results
    assert (
        first_result is True
    )  # First call should continue to process all eliminations
    assert (
        second_result is False
    )  # Second call should detect single player and end game
    assert len(eliminated_players) == 2  # Two players should be eliminated
    assert len(game.table) == 1  # Only one player should remain
    assert game.table[0].name == "Alice"  # Alice should be the remaining player


def test_handle_player_eliminations_returns_false_no_players(game, player_factory):
    """Test that _handle_player_eliminations returns False when no players remain."""
    # Create players - all without chips
    players = [
        player_factory(name="Alice", chips=0),
        player_factory(name="Bob", chips=0),
        player_factory(name="Charlie", chips=0),
    ]
    game.table.players = players
    eliminated_players = []

    # Need multiple calls to process all eliminations
    results = []
    while len(game.table) > 0:
        results.append(game._handle_player_eliminations(eliminated_players))

    # Verify results
    assert results[-1] is False  # Final call should return False
    assert len(eliminated_players) == 3  # All players should be eliminated
    assert len(game.table) == 0  # No players should remain


def test_handle_player_eliminations_returns_true_multiple_players(game, player_factory):
    """Test that _handle_player_eliminations returns True when multiple players remain."""
    # Create players - two with chips, one without
    players = [
        player_factory(name="Alice", chips=1000),
        player_factory(name="Bob", chips=1000),
        player_factory(name="Charlie", chips=0),
    ]
    game.table.players = players
    eliminated_players = []

    # Run elimination handling
    result = game._handle_player_eliminations(eliminated_players)

    # Verify results
    assert result is True  # Should return True to continue game
    assert len(eliminated_players) == 1  # One player should be eliminated
    assert len(game.table) == 2  # Two players should remain
    assert all(
        p.name in ["Alice", "Bob"] for p in game.table
    )  # Verify remaining players


def test_game_ends_when_one_player_remains(game, player_factory):
    """Test that game ends immediately when only one player remains."""
    # Create proper Agent instances instead of Mocks
    players = [
        Agent(name="Alice", chips=1000),
        Agent(name="Bob", chips=0),  # Will be eliminated
        Agent(name="Charlie", chips=0),  # Will be eliminated
    ]
    game.table.players = players

    # Mock _log_game_summary to verify it's called
    game._log_game_summary = MagicMock()

    # Run the game
    game.play_game()

    # Verify game ended after eliminations
    assert game.round_number <= 2  # Game should end in first or second round
    assert len(game.table) == 1  # Only Alice should remain
    assert game.table[0].name == "Alice"

    # Verify game summary was logged
    game._log_game_summary.assert_called_once()
