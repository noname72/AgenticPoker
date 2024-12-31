import pytest
from unittest.mock import Mock
from game.pot_manager import PotManager
from game.player import Player
from game.types import SidePot


@pytest.fixture
def pot_manager():
    return PotManager()


@pytest.fixture
def mock_players():
    """Create a set of mock players with different chip stacks."""
    return [
        Player("Alice", 1000),
        Player("Bob", 500),
        Player("Charlie", 200),
    ]


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing log output."""
    return Mock()


class TestPotManager:
    def test_initialization(self, pot_manager):
        """Test initial state of PotManager."""
        assert pot_manager.pot == 0
        assert pot_manager.side_pots is None

    def test_add_to_pot(self, pot_manager):
        """Test adding chips to the pot."""
        pot_manager.add_to_pot(100)
        assert pot_manager.pot == 100

        pot_manager.add_to_pot(50)
        assert pot_manager.pot == 150

    def test_reset_pot(self, pot_manager):
        """Test resetting the pot state."""
        # Setup some initial state
        pot_manager.pot = 500
        pot_manager.side_pots = [SidePot(100, [])]

        # Reset
        pot_manager.reset_pot()

        # Verify reset state
        assert pot_manager.pot == 0
        assert pot_manager.side_pots is None

    def test_calculate_side_pots_no_all_ins(self, pot_manager, mock_players):
        """Test side pot calculation with no all-in players."""
        posted_amounts = {
            mock_players[0]: 100,  # Alice bets 100
            mock_players[1]: 100,  # Bob matches
            mock_players[2]: 100,  # Charlie matches
        }

        side_pots = pot_manager.calculate_side_pots(posted_amounts)

        # Should be one pot with all players
        assert len(side_pots) == 1
        assert side_pots[0].amount == 300
        assert len(side_pots[0].eligible_players) == 3

    def test_calculate_side_pots_with_all_ins(self, pot_manager, mock_players):
        """Test side pot calculation with multiple all-in players."""
        posted_amounts = {
            mock_players[0]: 300,  # Alice bets 300
            mock_players[1]: 200,  # Bob all-in with 200
            mock_players[2]: 100,  # Charlie all-in with 100
        }

        side_pots = pot_manager.calculate_side_pots(posted_amounts)

        # Should create three pots
        assert len(side_pots) == 3

        # First pot (everyone contributes 100)
        assert side_pots[0].amount == 300
        assert len(side_pots[0].eligible_players) == 3

        # Second pot (Alice and Bob contribute 100 more)
        assert side_pots[1].amount == 200
        assert len(side_pots[1].eligible_players) == 2
        assert mock_players[2] not in side_pots[1].eligible_players

        # Third pot (Alice's extra 100)
        assert side_pots[2].amount == 100
        assert len(side_pots[2].eligible_players) == 1
        assert side_pots[2].eligible_players[0] == mock_players[0]

    def test_calculate_side_pots_empty_input(self, pot_manager):
        """Test side pot calculation with empty input."""
        side_pots = pot_manager.calculate_side_pots({})
        assert len(side_pots) == 0
        assert pot_manager.side_pots == []

    def test_get_side_pots_view_no_pots(self, pot_manager):
        """Test getting side pots view when no side pots exist."""
        view = pot_manager.get_side_pots_view()
        assert view == []

    def test_get_side_pots_view_with_pots(self, pot_manager, mock_players):
        """Test getting formatted view of side pots."""
        # Setup some side pots
        pot_manager.side_pots = [
            SidePot(300, mock_players),  # All players
            SidePot(200, mock_players[:2]),  # Just Alice and Bob
        ]

        view = pot_manager.get_side_pots_view()

        assert len(view) == 2
        assert view[0] == {
            "amount": 300,
            "eligible_players": ["Alice", "Bob", "Charlie"],
        }
        assert view[1] == {"amount": 200, "eligible_players": ["Alice", "Bob"]}

    def test_log_side_pots_no_pots(self, pot_manager, mock_logger):
        """Test logging when no side pots exist."""
        pot_manager.log_side_pots(mock_logger)
        mock_logger.info.assert_not_called()

    def test_log_side_pots_with_pots(self, pot_manager, mock_players, mock_logger):
        """Test logging of side pots."""
        # Setup side pots
        pot_manager.side_pots = [
            SidePot(300, mock_players),
            SidePot(200, mock_players[:2]),
        ]

        pot_manager.log_side_pots(mock_logger)

        # Verify logging calls
        assert mock_logger.info.call_count == 3  # Header + 2 pots
        mock_logger.info.assert_any_call("\nSide pots:")
        mock_logger.info.assert_any_call(
            "  Pot 1: $300 (Eligible: Alice, Bob, Charlie)"
        )
        mock_logger.info.assert_any_call("  Pot 2: $200 (Eligible: Alice, Bob)")

    def test_calculate_side_pots_equal_bets(self, pot_manager, mock_players):
        """Test side pot calculation when all players bet the same amount."""
        posted_amounts = {player: 100 for player in mock_players}

        side_pots = pot_manager.calculate_side_pots(posted_amounts)

        assert len(side_pots) == 1
        assert side_pots[0].amount == 300
        assert set(side_pots[0].eligible_players) == set(mock_players)

    def test_calculate_side_pots_zero_bets(self, pot_manager, mock_players):
        """Test side pot calculation when some players bet zero."""
        posted_amounts = {mock_players[0]: 100, mock_players[1]: 0, mock_players[2]: 0}

        side_pots = pot_manager.calculate_side_pots(posted_amounts)

        assert len(side_pots) == 1
        assert side_pots[0].amount == 100
        assert len(side_pots[0].eligible_players) == 1
        assert side_pots[0].eligible_players[0] == mock_players[0]

    def test_add_to_pot_negative_amount(self, pot_manager):
        """Test adding negative amount to pot raises ValueError."""
        initial_pot = pot_manager.pot
        with pytest.raises(ValueError, match="Cannot add negative amount to pot"):
            pot_manager.add_to_pot(-50)
        assert pot_manager.pot == initial_pot  # Pot should remain unchanged

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (100, 100),  # Normal positive amount
            (0, 0),  # Zero amount is allowed
        ],
    )
    def test_add_to_pot_various_amounts(self, pot_manager, test_input, expected):
        """Test adding various valid amounts to pot."""
        initial_pot = pot_manager.pot
        pot_manager.add_to_pot(test_input)
        assert pot_manager.pot == initial_pot + expected

    def test_calculate_side_pots_single_player(self, pot_manager, mock_players):
        """Test side pot calculation with only one player betting."""
        posted_amounts = {mock_players[0]: 100}
        
        side_pots = pot_manager.calculate_side_pots(posted_amounts)
        
        assert len(side_pots) == 1
        assert side_pots[0].amount == 100
        assert len(side_pots[0].eligible_players) == 1

    def test_calculate_side_pots_uneven_bets(self, pot_manager, mock_players):
        """Test side pot calculation with uneven bet amounts."""
        posted_amounts = {
            mock_players[0]: 123,  # Odd amount
            mock_players[1]: 456,  # Larger odd amount
            mock_players[2]: 789,  # Even larger odd amount
        }
        
        side_pots = pot_manager.calculate_side_pots(posted_amounts)
        
        assert len(side_pots) == 3
        # First pot: all contribute 123
        assert side_pots[0].amount == 369  # 123 * 3
        assert len(side_pots[0].eligible_players) == 3
        # Second pot: two players contribute 333 (456-123) more
        assert side_pots[1].amount == 666  # (456-123) * 2
        assert len(side_pots[1].eligible_players) == 2
        # Third pot: one player contributes 333 (789-456) more
        assert side_pots[2].amount == 333  # 789-456
        assert len(side_pots[2].eligible_players) == 1

    def test_calculate_side_pots_identical_all_ins(self, pot_manager, mock_players):
        """Test side pot calculation when multiple players are all-in for same amount."""
        posted_amounts = {
            mock_players[0]: 100,  # All-in
            mock_players[1]: 100,  # All-in same amount
            mock_players[2]: 200,  # Active player
        }
        
        side_pots = pot_manager.calculate_side_pots(posted_amounts)
        
        assert len(side_pots) == 2
        # First pot: everyone contributes 100
        assert side_pots[0].amount == 300
        assert len(side_pots[0].eligible_players) == 3
        # Second pot: only player 3 contributes 100 more
        assert side_pots[1].amount == 100
        assert len(side_pots[1].eligible_players) == 1
        assert side_pots[1].eligible_players[0] == mock_players[2]

    def test_calculate_side_pots_max_int(self, pot_manager, mock_players):
        """Test side pot calculation with very large numbers."""
        large_amount = 2**31 - 1  # Max 32-bit integer
        posted_amounts = {
            mock_players[0]: large_amount,
            mock_players[1]: large_amount // 2,
            mock_players[2]: large_amount // 4,
        }
        
        side_pots = pot_manager.calculate_side_pots(posted_amounts)
        
        assert len(side_pots) == 3
        # Verify no integer overflow
        assert all(pot.amount > 0 for pot in side_pots)
        assert all(isinstance(pot.amount, int) for pot in side_pots)

    def test_side_pots_view_empty_eligible_list(self, pot_manager):
        """Test getting side pots view with empty eligible players list."""
        pot_manager.side_pots = [SidePot(100, [])]
        
        view = pot_manager.get_side_pots_view()
        
        assert len(view) == 1
        assert view[0] == {"amount": 100, "eligible_players": []}

    def test_calculate_side_pots_duplicate_players(self, pot_manager, mock_players):
        """Test side pot calculation handles duplicate player entries correctly."""
        # Create a dict with duplicate player (shouldn't happen in practice)
        posted_amounts = {
            mock_players[0]: 100,
            mock_players[0]: 200,  # Duplicate key, should use last value
            mock_players[1]: 300,
        }
        
        side_pots = pot_manager.calculate_side_pots(posted_amounts)
        
        # Should only count each player once
        assert len(side_pots) > 0
        for pot in side_pots:
            # Check no duplicate players in eligible lists
            assert len(pot.eligible_players) == len(set(pot.eligible_players))

    def test_add_to_pot_max_int(self, pot_manager):
        """Test adding maximum integer value to pot."""
        max_int = 2**31 - 1
        pot_manager.add_to_pot(max_int)
        assert pot_manager.pot == max_int
        
        # Adding more should still work
        pot_manager.add_to_pot(100)
        assert pot_manager.pot == max_int + 100

    def test_reset_pot_idempotent(self, pot_manager):
        """Test that multiple reset_pot calls are idempotent."""
        # Setup initial state
        pot_manager.pot = 500
        pot_manager.side_pots = [SidePot(100, [])]
        
        # First reset
        pot_manager.reset_pot()
        assert pot_manager.pot == 0
        assert pot_manager.side_pots is None
        
        # Second reset should have same result
        pot_manager.reset_pot()
        assert pot_manager.pot == 0
        assert pot_manager.side_pots is None
