from unittest.mock import Mock

import pytest

from exceptions import InvalidGameStateError
from game.player import Player
from game.pot_manager import PotManager
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
        active_players = mock_players.copy()
        # All players bet 100 and have chips remaining
        for player in active_players[:3]:
            player.bet = 100
            player.chips = 900  # Started with 1000, bet 100

        side_pots = pot_manager.calculate_side_pots(active_players, [])

        # Should be one main pot with all players
        assert len(side_pots) == 1
        assert side_pots[0].amount == 300  # 100 * 3 players
        assert len(side_pots[0].eligible_players) == 3

    def test_calculate_side_pots_with_all_ins(self, pot_manager, mock_players):
        """Test side pot calculation with multiple all-in players."""
        active_players = mock_players.copy()

        # Player 1 has enough chips and bets 300
        mock_players[0].bet = 300
        mock_players[0].chips = 700  # Started with 1000

        # Player 2 goes all-in for 200
        mock_players[1].bet = 200
        mock_players[1].chips = 0  # All-in

        # Player 3 goes all-in for 100
        mock_players[2].bet = 100
        mock_players[2].chips = 0  # All-in

        all_in_players = [mock_players[2], mock_players[1]]  # Ordered by bet size

        side_pots = pot_manager.calculate_side_pots(active_players, all_in_players)

        # Should create three pots
        assert len(side_pots) == 3

        # Main pot - all players contribute 100
        assert side_pots[0].amount == 300  # 100 * 3
        assert len(side_pots[0].eligible_players) == 3
        assert all(p in side_pots[0].eligible_players for p in mock_players)

        # First side pot - P1 and P2 contribute additional 100
        assert side_pots[1].amount == 200  # 100 * 2
        assert len(side_pots[1].eligible_players) == 2
        assert mock_players[0] in side_pots[1].eligible_players
        assert mock_players[1] in side_pots[1].eligible_players
        assert mock_players[2] not in side_pots[1].eligible_players

        # Second side pot - only P1's additional 100
        assert side_pots[2].amount == 100
        assert len(side_pots[2].eligible_players) == 1
        assert side_pots[2].eligible_players[0] == mock_players[0]

    def test_calculate_side_pots_empty_input(self, pot_manager):
        """Test side pot calculation with empty input."""
        side_pots = pot_manager.calculate_side_pots([], [])
        assert len(side_pots) == 0
        # The side_pots property should remain None since no pots were created
        assert pot_manager.side_pots is None

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
        active_players = mock_players.copy()

        # All players bet 100 and have chips remaining
        for player in active_players:
            player.bet = 100
            player.chips = 900  # Started with 1000

        side_pots = pot_manager.calculate_side_pots(active_players, [])

        # Should be single main pot since no all-ins
        assert len(side_pots) == 1
        assert side_pots[0].amount == 300  # 100 * 3 players
        assert len(side_pots[0].eligible_players) == 3
        assert set(side_pots[0].eligible_players) == set(active_players)

    def test_calculate_side_pots_zero_bets(self, pot_manager, mock_players):
        """Test side pot calculation when some players haven't bet."""
        active_players = mock_players.copy()

        # Only first player bets
        mock_players[0].bet = 100
        mock_players[0].chips = 900
        mock_players[1].bet = 0
        mock_players[1].chips = 500  # Original amount
        mock_players[2].bet = 0
        mock_players[2].chips = 200  # Original amount

        side_pots = pot_manager.calculate_side_pots(active_players, [])

        # Should be single pot with only the betting player
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
        active_players = mock_players.copy()

        # Only first player bets
        mock_players[0].bet = 100
        mock_players[0].chips = 900
        mock_players[1].bet = 0
        mock_players[1].chips = 500
        mock_players[2].bet = 0
        mock_players[2].chips = 200

        side_pots = pot_manager.calculate_side_pots(active_players, [])

        # Should be single pot with only the betting player
        assert len(side_pots) == 1
        assert side_pots[0].amount == 100
        assert len(side_pots[0].eligible_players) == 1
        assert side_pots[0].eligible_players[0] == mock_players[0]

    def test_calculate_side_pots_uneven_bets(self, pot_manager, mock_players):
        """Test side pot calculation with uneven bet amounts and all-ins."""
        active_players = mock_players.copy()

        # P1 bets 500
        mock_players[0].bet = 500
        mock_players[0].chips = 500  # Started with 1000

        # P2 all-in for 400
        mock_players[1].bet = 400
        mock_players[1].chips = 0  # All-in

        # P3 all-in for 200
        mock_players[2].bet = 200
        mock_players[2].chips = 0  # All-in

        all_in_players = [mock_players[2], mock_players[1]]  # Ordered by bet size

        side_pots = pot_manager.calculate_side_pots(active_players, all_in_players)

        assert len(side_pots) == 3
        # Main pot: all contribute 200
        assert side_pots[0].amount == 600  # 200 * 3
        assert len(side_pots[0].eligible_players) == 3

        # First side pot: P1 and P2 contribute 200 more
        assert side_pots[1].amount == 400  # 200 * 2
        assert len(side_pots[1].eligible_players) == 2
        assert mock_players[2] not in side_pots[1].eligible_players

        # Second side pot: P1's final 100
        assert side_pots[2].amount == 100
        assert len(side_pots[2].eligible_players) == 1
        assert side_pots[2].eligible_players[0] == mock_players[0]

    def test_calculate_side_pots_duplicate_players(self, pot_manager, mock_players):
        """Test side pot calculation handles duplicate player entries correctly."""
        active_players = mock_players.copy()

        # Setup players with one duplicate (shouldn't happen in practice)
        mock_players[0].bet = 200
        mock_players[0].chips = 800
        duplicate_player = mock_players[0]  # Same player reference
        duplicate_player.bet = 200  # Should not create separate pot
        mock_players[1].bet = 300
        mock_players[1].chips = 200

        all_in_players = [mock_players[1]]  # P1 is all-in

        side_pots = pot_manager.calculate_side_pots(active_players, all_in_players)

        # Should only count each player once
        assert len(side_pots) == 2
        for pot in side_pots:
            # Check no duplicate players in eligible lists
            assert len(pot.eligible_players) == len(set(pot.eligible_players))
            # Verify pot amounts are correct
            if len(pot.eligible_players) == 2:
                assert pot.amount == 400  # Both players contribute 200
            else:
                assert pot.amount == 100  # P1's extra 100

    def test_calculate_side_pots_identical_all_ins(self, pot_manager, mock_players):
        """Test when multiple players go all-in for the same amount."""
        active_players = mock_players.copy()

        # P1 has chips and bets 200
        mock_players[0].bet = 200
        mock_players[0].chips = 800

        # P2 and P3 both go all-in for 100
        mock_players[1].bet = 100
        mock_players[1].chips = 0
        mock_players[2].bet = 100
        mock_players[2].chips = 0

        all_in_players = [
            mock_players[1],
            mock_players[2],
        ]  # Both all-in for same amount

        side_pots = pot_manager.calculate_side_pots(active_players, all_in_players)

        assert len(side_pots) == 2
        # Main pot - everyone contributed 100
        assert side_pots[0].amount == 300
        assert len(side_pots[0].eligible_players) == 3
        assert all(p in side_pots[0].eligible_players for p in mock_players)

        # Side pot - only P1's extra 100
        assert side_pots[1].amount == 100
        assert len(side_pots[1].eligible_players) == 1
        assert side_pots[1].eligible_players[0] == mock_players[0]

    def test_calculate_side_pots_max_int(self, pot_manager, mock_players):
        """Test side pot calculation with very large bets."""
        active_players = mock_players.copy()
        large_bet = 2**31 - 1  # Max 32-bit integer

        # P1 bets max int
        mock_players[0].bet = large_bet
        mock_players[0].chips = 1000  # Has chips remaining

        # P2 all-in for half max int
        mock_players[1].bet = large_bet // 2
        mock_players[1].chips = 0  # All-in

        # P3 all-in for quarter max int
        mock_players[2].bet = large_bet // 4
        mock_players[2].chips = 0  # All-in

        all_in_players = [mock_players[2], mock_players[1]]

        side_pots = pot_manager.calculate_side_pots(active_players, all_in_players)

        quarter = large_bet // 4
        half = large_bet // 2

        assert len(side_pots) == 3
        # Verify no integer overflow
        assert all(pot.amount > 0 for pot in side_pots)
        assert all(isinstance(pot.amount, int) for pot in side_pots)

        # Main pot - all players contribute quarter
        assert side_pots[0].amount == quarter * 3
        assert len(side_pots[0].eligible_players) == 3

        # First side pot - P1 and P2 contribute up to half
        assert side_pots[1].amount == (half - quarter) * 2
        assert len(side_pots[1].eligible_players) == 2

        # Second side pot - P1's remainder
        assert side_pots[2].amount == large_bet - half
        assert len(side_pots[2].eligible_players) == 1

    def test_side_pots_view_empty_eligible_list(self, pot_manager):
        """Test getting side pots view with empty eligible players list."""
        pot_manager.side_pots = [SidePot(100, [])]

        view = pot_manager.get_side_pots_view()

        assert len(view) == 1
        assert view[0] == {"amount": 100, "eligible_players": []}

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

    def test_calculate_side_pots_equal_all_ins(self, pot_manager, mock_players):
        """Test side pot calculation when multiple players go all-in for equal amounts."""
        active_players = mock_players.copy()

        # P1 bets 300 and has chips remaining
        mock_players[0].bet = 300
        mock_players[0].chips = 700

        # P2 and P3 both go all-in for exactly 200
        mock_players[1].bet = 200
        mock_players[1].chips = 0  # All-in
        mock_players[2].bet = 200
        mock_players[2].chips = 0  # All-in

        all_in_players = [
            mock_players[1],
            mock_players[2],
        ]  # Both all-in for same amount

        side_pots = pot_manager.calculate_side_pots(active_players, all_in_players)

        assert len(side_pots) == 2

        # Main pot - everyone contributes 200
        assert side_pots[0].amount == 600  # 200 * 3
        assert len(side_pots[0].eligible_players) == 3
        assert all(p in side_pots[0].eligible_players for p in mock_players)

        # Side pot - only P1's extra 100
        assert side_pots[1].amount == 100
        assert len(side_pots[1].eligible_players) == 1
        assert side_pots[1].eligible_players[0] == mock_players[0]

        # Verify total pot amount matches total bets
        total_bets = sum(p.bet for p in mock_players)
        total_pots = sum(pot.amount for pot in side_pots)
        assert total_pots == total_bets

    def test_validate_pot_state(self, pot_manager, mock_players):
        """Test pot state validation."""
        # Setup valid state
        pot_manager.pot = 300
        for player in mock_players:
            player.bet = 100
            player.chips = 900

        # Should pass validation
        assert pot_manager.validate_pot_state(mock_players)

        # Setup invalid state
        pot_manager.pot = 400  # More in pot than bets

        # Should raise error
        with pytest.raises(InvalidGameStateError):
            pot_manager.validate_pot_state(mock_players)

    def test_validate_pot_state_total_chips(self, pot_manager, mock_players):
        """Test pot state validation including total chips consistency."""
        # Setup initial state
        initial_chips = 1000
        for player in mock_players:
            player.chips = initial_chips
            player.bet = 0
        
        # Calculate initial total
        initial_total = sum(p.chips for p in mock_players)
        
        # Should pass validation
        assert pot_manager.validate_pot_state(mock_players, initial_total)
        
        # Setup valid betting state - total chips should remain constant
        pot_manager.pot = 300
        for player in mock_players:
            player.bet = 100
            player.chips = 900  # Started with 1000, bet 100
        
        # Should still pass validation since total chips haven't changed
        assert pot_manager.validate_pot_state(mock_players, initial_total)
        
        # Setup invalid state where chips disappeared
        mock_players[0].chips = 800  # Lost 100 chips that aren't in pot
        
        # Should raise error
        with pytest.raises(InvalidGameStateError, match="Total chips changed"):
            pot_manager.validate_pot_state(mock_players, initial_total)
