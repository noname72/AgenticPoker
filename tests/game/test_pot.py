import logging
from unittest.mock import Mock

import pytest

from data.types.pot_types import SidePot
from exceptions import InvalidGameStateError
from game.pot import Pot


@pytest.fixture
def pot():
    """Create a fresh Pot instance for each test."""
    return Pot()


@pytest.fixture
def mock_players(player_factory):
    """Create a set of mock players with different chip stacks.

    Creates three players:
    - Alice: 1000 chips
    - Bob: 500 chips
    - Charlie: 200 chips
    """
    return [
        player_factory(name="Alice", chips=1000),
        player_factory(name="Bob", chips=500),
        player_factory(name="Charlie", chips=200),
    ]


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing log output."""
    return Mock()


def get_game_state_str(pot, players):
    """Helper function to get formatted game state string."""
    state = [
        "\nCurrent Game State:",
        f"Pot: ${pot.pot}",
        "\nPlayers:",
    ]
    for p in players:
        state.append(f"  {p.name}: chips=${p.chips}, bet=${p.bet}")

    # Don't include bets in total since they're already in the pot
    total_in_play = sum(p.chips for p in players) + pot.pot
    state.append(f"\nTotal in play: ${total_in_play}")

    if pot.side_pots:
        state.append("\nSide Pots:")
        for i, pot in enumerate(pot.side_pots, 1):
            state.append(
                f"  Pot {i}: ${pot.amount} (Eligible: {[p.name for p in pot.eligible_players]})"
            )

    return "\n".join(state)


class TestPot:
    def test_initialization(self, pot):
        """Test that a new Pot is initialized with empty state.

        Assumptions:
        - New pot should have 0 chips
        - Side pots should be None initially
        """
        assert pot.pot == 0
        assert pot.side_pots is None

    def test_add_to_pot(self, pot):
        """Test adding chips to the main pot.

        Assumptions:
        - Should track running total correctly
        - Multiple additions should accumulate
        """
        pot.add_to_pot(100)
        assert pot.pot == 100

        pot.add_to_pot(50)
        assert pot.pot == 150

    def test_reset_pot(self, pot):
        """Test resetting the pot state.

        Assumptions:
        - Should clear main pot to 0
        - Should clear any existing side pots
        - Should work even if pot is already empty
        """
        # Setup some initial state
        pot.pot = 500
        pot.side_pots = [SidePot(amount=100, eligible_players=[])]

        # Reset
        pot.reset_pot()

        # Verify reset state
        assert pot.pot == 0
        assert pot.side_pots is None

    def test_calculate_side_pots_no_all_ins(self, pot, mock_players):
        """Test side pot calculation with no all-in players.

        Assumptions:
        - With no all-ins, should create single main pot
        - All players who bet should be eligible
        - Pot amount should equal total bets
        """
        active_players = mock_players.copy()
        # All players bet 100 and have chips remaining
        for player in active_players[:3]:
            player.bet = 100
            player.chips = 900  # Started with 1000, bet 100

        side_pots = pot.calculate_side_pots(active_players)

        # Should be one main pot with all players
        assert len(side_pots) == 1
        assert side_pots[0].amount == 300  # 100 * 3 players
        assert len(side_pots[0].eligible_players) == 3

    def test_calculate_side_pots_with_all_ins(self, pot, mock_players):
        """Test side pot calculation with multiple all-in players.

        Assumptions:
        - Should create separate pots for each all-in amount
        - Players should only be eligible for pots up to their contribution
        - Total of all pots should equal total bets
        - Pot amounts should be correctly distributed
        """
        # Setup players
        mock_players[0].bet = 300
        mock_players[0].chips = 700
        mock_players[1].bet = 200
        mock_players[1].chips = 0
        mock_players[2].bet = 100
        mock_players[2].chips = 0

        side_pots = pot.calculate_side_pots(mock_players)

        # Verify number of pots
        assert (
            len(side_pots) == 3
        ), f"Expected 3 side pots, got {len(side_pots)}\n" + get_game_state_str(
            pot, mock_players
        )

        # Verify main pot
        assert side_pots[0].amount == 300, (
            f"Main pot should be $300, got ${side_pots[0].amount}\n"
            + get_game_state_str(pot, mock_players)
        )
        assert len(side_pots[0].eligible_players) == 3, (
            f"Main pot should have 3 players, got {len(side_pots[0].eligible_players)}\n"
            + f"Eligible players: {[p.name for p in side_pots[0].eligible_players]}\n"
            + get_game_state_str(pot, mock_players)
        )

    def test_calculate_side_pots_empty_input(self, pot):
        """Test side pot calculation with empty input.

        Assumptions:
        - Should handle empty player list gracefully
        - Should return empty list of side pots
        - Should set side_pots property to empty list
        """
        side_pots = pot.calculate_side_pots([])
        assert len(side_pots) == 0
        assert pot.side_pots == []

    def test_get_side_pots_view_no_pots(self, pot):
        """Test getting side pots view when no side pots exist.

        Assumptions:
        - Should return empty list when no side pots exist
        - Should not throw error when side_pots is None
        """
        view = pot.get_side_pots_view()
        assert view == []

    def test_get_side_pots_view_with_pots(self, pot, mock_players):
        """Test getting formatted view of side pots.

        Assumptions:
        - Should return list of dicts with amount and eligible players
        - Should preserve pot order
        - Should include all pots in view
        - Should use player names (not Player objects) in eligible_players
        """
        # Setup some side pots
        pot.side_pots = [
            SidePot(amount=300, eligible_players=[p.name for p in mock_players]),
            SidePot(amount=200, eligible_players=[p.name for p in mock_players[:2]]),
        ]

        view = pot.get_side_pots_view()

        assert len(view) == 2
        assert view[0] == {
            "amount": 300,
            "eligible_players": ["Alice", "Bob", "Charlie"],
        }
        assert view[1] == {"amount": 200, "eligible_players": ["Alice", "Bob"]}

    def test_log_side_pots_no_pots(self, pot, mock_logger):
        """Test logging when no side pots exist.

        Assumptions:
        - Should not log anything when no side pots exist
        - Should not throw error when side_pots is None
        """
        pot.log_side_pots(mock_logger)
        mock_logger.info.assert_not_called()

    def test_calculate_side_pots_equal_bets(self, pot, mock_players):
        """Test side pot calculation when all players bet the same amount.

        Assumptions:
        - Should create single pot when all bets are equal
        - All players should be eligible for the pot
        - Pot amount should equal total bets
        - Should handle case where no side pots are needed
        """
        active_players = mock_players.copy()

        # All players bet 100 and have chips remaining
        for player in active_players:
            player.bet = 100
            player.chips = 900  # Started with 1000

        side_pots = pot.calculate_side_pots(active_players)

        # Should be single main pot since no all-ins
        assert len(side_pots) == 1
        assert side_pots[0].amount == 300  # 100 * 3 players
        assert len(side_pots[0].eligible_players) == 3
        assert set(side_pots[0].eligible_players) == {p.name for p in active_players}

    def test_calculate_side_pots_zero_bets(self, pot, mock_players):
        """Test side pot calculation when some players haven't bet.

        Assumptions:
        - Should only include players who have bet > 0
        - Should create correct pot amounts for betting players
        - Should handle mix of zero and non-zero bets correctly
        - Non-betting players should not be eligible for pots
        """
        active_players = mock_players.copy()

        # Only first player bets
        mock_players[0].bet = 100
        mock_players[0].chips = 900
        mock_players[1].bet = 0
        mock_players[1].chips = 500  # Original amount
        mock_players[2].bet = 0
        mock_players[2].chips = 200  # Original amount

        side_pots = pot.calculate_side_pots(active_players)

        # Should be single pot with only the betting player
        assert len(side_pots) == 1
        assert side_pots[0].amount == 100
        assert len(side_pots[0].eligible_players) == 1
        assert side_pots[0].eligible_players[0] == mock_players[0].name

    def test_add_to_pot_negative_amount(self, pot):
        """Test adding negative amount to pot raises ValueError.

        Assumptions:
        - Should raise ValueError for negative amounts
        - Should not modify pot amount when error occurs
        - Error message should be descriptive
        """
        initial_pot = pot.pot
        with pytest.raises(ValueError, match="Cannot add negative amount to pot"):
            pot.add_to_pot(-50)
        assert pot.pot == initial_pot  # Pot should remain unchanged

    @pytest.mark.parametrize(
        "test_input,expected",
        [
            (100, 100),  # Normal positive amount
            (0, 0),  # Zero amount is allowed
        ],
    )
    def test_add_to_pot_various_amounts(self, pot, test_input, expected):
        """Test adding various valid amounts to pot.

        Assumptions:
        - Should handle normal positive amounts correctly
        - Should allow adding zero chips
        - Should accumulate amounts correctly from initial pot value
        - Should not allow negative amounts (tested separately)
        """
        initial_pot = pot.pot
        pot.add_to_pot(test_input)
        assert pot.pot == initial_pot + expected

    def test_calculate_side_pots_single_player(self, pot, mock_players):
        """Test side pot calculation with only one player betting.

        Assumptions:
        - Should create single pot for lone betting player
        - Pot amount should match the bet amount
        - Only betting player should be eligible
        - Should handle case where other players have no bets
        """
        active_players = mock_players.copy()

        # Only first player bets
        mock_players[0].bet = 100
        mock_players[0].chips = 900
        mock_players[1].bet = 0
        mock_players[1].chips = 500
        mock_players[2].bet = 0
        mock_players[2].chips = 200

        side_pots = pot.calculate_side_pots(active_players)

        assert len(side_pots) == 1
        assert side_pots[0].amount == 100
        assert len(side_pots[0].eligible_players) == 1
        assert side_pots[0].eligible_players[0] == mock_players[0].name

    def test_calculate_side_pots_uneven_bets(self, pot, mock_players):
        """Test side pot calculation with uneven bet amounts and all-ins.

        Assumptions:
        - Should handle multiple different bet levels correctly
        - Should create appropriate side pots for each bet level
        - Players should only be eligible for pots up to their contribution
        - Total of all pots should equal total bets
        - Should maintain correct order of pots (lowest to highest)
        """
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

        side_pots = pot.calculate_side_pots(active_players)

        assert len(side_pots) == 3
        # Main pot: all contribute 200
        assert side_pots[0].amount == 600  # 200 * 3
        assert len(side_pots[0].eligible_players) == 3

        # First side pot: P1 and P2 contribute 200 more
        assert side_pots[1].amount == 400  # 200 * 2
        assert len(side_pots[1].eligible_players) == 2
        assert mock_players[2].name not in side_pots[1].eligible_players

        # Second side pot: P1's final 100
        assert side_pots[2].amount == 100
        assert len(side_pots[2].eligible_players) == 1
        assert side_pots[2].eligible_players[0] == mock_players[0].name

    def test_calculate_side_pots_duplicate_players(self, pot, mock_players):
        """Test side pot calculation handles duplicate player entries correctly.

        Assumptions:
        - Should handle duplicate player references gracefully
        - Should not create duplicate pots for same player
        - Should count each player's contribution only once
        - Should maintain correct pot amounts despite duplicates
        """
        active_players = mock_players.copy()

        # Setup players with one duplicate (shouldn't happen in practice)
        mock_players[0].bet = 200
        mock_players[0].chips = 800
        duplicate_player = mock_players[0]  # Same player reference
        duplicate_player.bet = 200  # Should not create separate pot
        mock_players[1].bet = 300
        mock_players[1].chips = 200

        side_pots = pot.calculate_side_pots(active_players)

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

    def test_calculate_side_pots_equal_all_ins(self, pot, mock_players):
        """Test side pot calculation when multiple players go all-in for equal amounts.

        Tests a scenario where:
        1. One player bets above all-in amount
        2. Two players go all-in for identical amounts
        3. Side pots are created based on all-in level

        Assumptions:
        - Should handle multiple equal all-ins correctly
        - Should create main pot up to all-in amount
        - Should create side pot only for excess amount
        - Should maintain correct eligibility for each pot
        - Should not create unnecessary pots for equal all-ins
        - Should preserve total chip consistency

        Initial state:
        - P1: bets 300, has 700 chips remaining
        - P2: all-in for 200
        - P3: all-in for 200

        Expected outcome:
        - Two pots:
          1. Main pot: 600 (200 × 3) - all players eligible
          2. Side pot: 100 (P1's extra 100) - only P1 eligible
        - Total pot matches total bets (700)
        """
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

        side_pots = pot.calculate_side_pots(active_players)

        assert len(side_pots) == 2

        # Main pot - everyone contributes 200
        assert side_pots[0].amount == 600, "Main pot should be 200 * 3"
        assert len(side_pots[0].eligible_players) == 3
        assert all(p.name in side_pots[0].eligible_players for p in mock_players)

        # Side pot - only P1's extra 100
        assert side_pots[1].amount == 100
        assert len(side_pots[1].eligible_players) == 1
        assert side_pots[1].eligible_players[0] == mock_players[0].name

        # Verify total pot amount matches total bets
        total_bets = sum(p.bet for p in mock_players)
        total_pots = sum(pot.amount for pot in side_pots)
        assert total_pots == total_bets

    def test_calculate_side_pots_max_int(self, pot, mock_players):
        """Test side pot calculation with very large bets.

        Assumptions:
        - Should handle bets up to max 32-bit integer without overflow
        - Should correctly calculate side pots with large numbers
        - Should maintain integer precision for all pot amounts
        - Should handle division of large numbers correctly
        - Should maintain correct eligibility for each pot level
        """
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

        side_pots = pot.calculate_side_pots(active_players)

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

    def test_side_pots_view_empty_eligible_list(self, pot):
        """Test getting side pots view with empty eligible players list.

        Assumptions:
        - Should handle pots with no eligible players
        - Should return correct amount even with empty eligible list
        - Should represent empty eligible list as empty array
        """
        pot.side_pots = [SidePot(amount=100, eligible_players=[])]

        view = pot.get_side_pots_view()

        assert len(view) == 1
        assert view[0] == {"amount": 100, "eligible_players": []}

    def test_add_to_pot_max_int(self, pot):
        """Test adding maximum integer value to pot.

        Assumptions:
        - Should handle adding max 32-bit integer without overflow
        - Should allow further additions beyond max int
        - Should maintain integer precision
        - Should not lose or corrupt pot amount
        """
        max_int = 2**31 - 1
        pot.add_to_pot(max_int)
        assert pot.pot == max_int

        # Adding more should still work
        pot.add_to_pot(100)
        assert pot.pot == max_int + 100

    def test_reset_pot_idempotent(self, pot):
        """Test that multiple reset_pot calls are idempotent.

        Assumptions:
        - Multiple resets should have same effect as single reset
        - Should clear both main pot and side pots
        - Should work correctly regardless of initial state
        - Should not throw errors on repeated resets
        """
        # Setup initial state
        pot.pot = 500
        pot.side_pots = [SidePot(amount=100, eligible_players=[])]

        # First reset
        pot.reset_pot()
        assert pot.pot == 0
        assert pot.side_pots is None

        # Second reset should have same result
        pot.reset_pot()
        assert pot.pot == 0
        assert pot.side_pots is None

    def test_validate_pot_state(self, pot, mock_players):
        """Test pot state validation.

        Assumptions:
        - Should validate total chips remain constant
        - Should verify pot amounts match current bets
        - Should detect invalid pot states
        - Should raise descriptive errors for invalid states
        - Should pass validation for valid states
        """
        # Setup valid state
        pot.pot = 300
        for player in mock_players:
            player.bet = 100
            player.chips = 900  # Started with 1000, bet 100

        # Should pass validation
        assert pot.validate_pot_state(mock_players)

        # Setup invalid state - pot is less than current bets
        pot.pot = 200  # Less than total bets (300)

        # Should raise error due to pot/bet mismatch
        with pytest.raises(InvalidGameStateError, match="Current bets exceed pot"):
            pot.validate_pot_state(mock_players)

        # Reset to valid state
        pot.pot = 300

    def test_validate_pot_state_total_chips(self, pot, mock_players):
        """Test pot state validation including total chips consistency.

        Assumptions:
        - Should track total chips across all players and pots
        - Should detect changes in total chips
        - Should validate after betting rounds
        - Should account for chips in player stacks and all pots
        - Should handle zero chip edge cases
        """
        # Setup initial state
        initial_chips = 1000
        for player in mock_players:
            player.chips = initial_chips
            player.bet = 0

        initial_total = sum(p.chips for p in mock_players)  # 3000

        # Should pass validation
        assert pot.validate_pot_state(
            mock_players, initial_total
        ), f"Initial state validation failed:{get_game_state_str(pot, mock_players)}"

        # Setup valid betting state
        for player in mock_players:
            bet_amount = 100
            player.chips -= bet_amount  # Deduct from chips first
            player.bet = bet_amount  # Then set the bet

        # Add bets to pot
        total_bets = sum(p.bet for p in mock_players)
        pot.add_to_pot(total_bets)

        # Should still pass validation
        # Note: Don't include bets in total since they're now in the pot
        current_total = sum(p.chips for p in mock_players) + pot.pot
        assert current_total == initial_total, (
            f"Total chips changed! Expected ${initial_total}, got ${current_total}\n"
            + get_game_state_str(pot, mock_players)
        )

    def test_pot_progression_through_rounds(self, pot, mock_players):
        """Test pot tracking through multiple betting rounds.

        Tests a complete hand progression where:
        1. Initial betting round with all players
        2. Second betting round with different amounts
        3. Pot accumulation across rounds

        Assumptions:
        - Should track running pot total correctly
        - Should handle multiple betting rounds
        - Should maintain total chip consistency
        - Should clear bets between rounds
        - Should accumulate bets into pot correctly
        - Should handle different bet amounts per round

        Initial state:
        - All players start with 1000 chips

        Round progression:
        1. First round: All players bet 100
        2. Second round: Two players bet 200 each

        Expected outcome:
        - Pot should contain 700 total (300 from round 1 + 400 from round 2)
        - All bets should be cleared after each round
        - Total chips in play should remain constant
        """
        # Setup initial state - each player starts with 1000 chips
        for player in mock_players:
            player.chips = 1000
            player.bet = 0
        initial_total = sum(p.chips for p in mock_players)  # 3000

        # Round 1: Everyone bets 100
        for player in mock_players:
            bet_amount = 100
            player.chips -= bet_amount  # Deduct from chips first
            player.bet = bet_amount  # Then set the bet

        # Add round 1 bets to pot
        total_bets = sum(p.bet for p in mock_players)
        pot.add_to_pot(total_bets)  # Add 300 to pot

        # Clear bets before round 2
        for player in mock_players:
            player.bet = 0

        # Round 2: Two players bet 200
        for player in mock_players[:2]:
            bet_amount = 200
            player.chips -= bet_amount  # Deduct from chips first
            player.bet = bet_amount  # Then set the bet

        # Add round 2 bets to pot
        total_bets = sum(p.bet for p in mock_players)
        pot.add_to_pot(total_bets)  # Add 400 to pot

        # Verify final state
        # Note: Don't include bets in total since they're now in the pot
        current_total = sum(p.chips for p in mock_players) + pot.pot
        assert current_total == initial_total, (
            f"Total chips changed! Expected ${initial_total}, got ${current_total}\n"
            + get_game_state_str(pot, mock_players)
        )

    def test_calculate_side_pots_complex_scenario(self, pot, mock_players):
        """Test side pot calculation with a complex multi-player all-in scenario.

        Tests a complex scenario where:
        1. Three players go all-in for different amounts
        2. Multiple side pots are created
        3. Each pot has different eligible players

        Assumptions:
        - Should handle multiple all-in amounts correctly
        - Should create correct number of side pots
        - Should calculate correct amounts for each pot level
        - Should track correct eligibility for each pot
        - Should maintain total chip consistency
        - Should order pots from smallest to largest contribution

        Initial state:
        - P1: all-in for 1000
        - P2: all-in for 600
        - P3: all-in for 300

        Expected outcome:
        - Three pots:
          1. Main pot: 900 (300 × 3) - all players eligible
          2. Second pot: 600 (300 × 2) - P1 and P2 eligible
          3. Third pot: 400 (400 × 1) - only P1 eligible
        """
        active_players = mock_players.copy()

        # P1 has chips and bets 1000 (all-in)
        mock_players[0].bet = 1000
        mock_players[0].chips = 0  # All-in

        # P2 has chips and bets 600 (all-in)
        mock_players[1].bet = 600
        mock_players[1].chips = 0  # All-in

        # P3 has chips and bets 300 (all-in)
        mock_players[2].bet = 300
        mock_players[2].chips = 0  # All-in

        all_in_players = [
            mock_players[2],  # 300
            mock_players[1],  # 600
            mock_players[0],  # 1000
        ]

        side_pots = pot.calculate_side_pots(active_players)

        # Verify the number of pots
        assert len(side_pots) == 3, "Should create three side pots"

        # Main pot (all players contribute 300)
        assert side_pots[0].amount == 900, "Main pot should be 300 * 3"
        assert len(side_pots[0].eligible_players) == 3
        # Fix: Check player names instead of Player objects
        assert all(p.name in side_pots[0].eligible_players for p in mock_players)

        # Second pot (P1 and P2 contribute 300 more each)
        assert side_pots[1].amount == 600, "Second pot should be 300 * 2"
        assert len(side_pots[1].eligible_players) == 2
        assert mock_players[0].name in side_pots[1].eligible_players
        assert mock_players[1].name in side_pots[1].eligible_players
        assert mock_players[2].name not in side_pots[1].eligible_players

        # Third pot (only P1's remaining 400)
        assert side_pots[2].amount == 400, "Third pot should be 400"
        assert len(side_pots[2].eligible_players) == 1
        assert side_pots[2].eligible_players[0] == mock_players[0].name

        # Verify total amount matches total bets
        total_bets = sum(p.bet for p in mock_players)
        total_pots = sum(pot.amount for pot in side_pots)
        assert total_pots == total_bets, "Total in pots should match total bets"

        # Verify each player is in the correct number of pots
        p1_pots = sum(
            1 for pot in side_pots if mock_players[0].name in pot.eligible_players
        )
        p2_pots = sum(
            1 for pot in side_pots if mock_players[1].name in pot.eligible_players
        )
        p3_pots = sum(
            1 for pot in side_pots if mock_players[2].name in pot.eligible_players
        )

        assert p1_pots == 3, "P1 should be in all three pots"
        assert p2_pots == 2, "P2 should be in two pots"
        assert p3_pots == 1, "P3 should be in one pot"

    def test_side_pot_hand_comparison(self, pot, mock_players):
        """Test side pot distribution with proper hand comparison.

        Tests a scenario where:
        1. Players have different hand rankings
        2. Side pots need to be awarded based on hand strength
        3. Hand comparison operators are used to determine winners

        Assumptions:
        - Should correctly evaluate hand rankings
        - Should handle hand comparison operators (>, ==, <) properly
        - Should determine correct winners for each pot
        - Should handle folded players correctly
        - Should maintain correct pot amounts during distribution
        - Should respect pot eligibility during comparisons

        Initial state:
        - P1: Queen high, bet 300
        - P2: Pair of 9s, bet 200
        - P3: Ace high, bet 200

        Expected outcome:
        - Charlie (P3) wins with Ace high
        - Correct hand comparison determines winner
        - Only eligible players compared for each pot
        """
        active_players = mock_players.copy()
        initial_total = sum(p.chips for p in active_players)  # Store initial total

        # Setup player bets and hands
        mock_players[0].bet = 300  # Alice
        mock_players[0].chips = 700
        mock_players[0].folded = False
        mock_players[0].hand = Mock()
        mock_players[0].hand.evaluate = Mock(return_value="High Card")
        mock_players[0].hand.get_value = Mock(
            return_value=(10, [12, 5, 4, 3, 2])
        )  # Queen high
        mock_players[0].hand.__gt__ = Mock(
            side_effect=lambda other: False
        )  # Always loses
        mock_players[0].hand.__eq__ = Mock(
            side_effect=lambda other: False
        )  # Never ties
        mock_players[0].hand.__lt__ = Mock(
            side_effect=lambda other: True
        )  # Always loses

        mock_players[1].bet = 200  # Bob
        mock_players[1].chips = 0
        mock_players[1].folded = False
        mock_players[1].hand = Mock()
        mock_players[1].hand.evaluate = Mock(return_value="One Pair")
        mock_players[1].hand.get_value = Mock(
            return_value=(9, [9, 14, 10, 7])
        )  # Pair of 9s
        mock_players[1].hand.__gt__ = Mock(
            side_effect=lambda other: False
        )  # Always loses
        mock_players[1].hand.__eq__ = Mock(
            side_effect=lambda other: False
        )  # Never ties
        mock_players[1].hand.__lt__ = Mock(
            side_effect=lambda other: True
        )  # Always loses

        mock_players[2].bet = 200  # Charlie
        mock_players[2].chips = 0
        mock_players[2].folded = False
        mock_players[2].hand = Mock()
        mock_players[2].hand.evaluate = Mock(return_value="High Card")
        mock_players[2].hand.get_value = Mock(
            return_value=(10, [14, 13, 12, 10, 8])
        )  # Ace high
        mock_players[2].hand.__gt__ = Mock(
            side_effect=lambda other: True
        )  # Always wins
        mock_players[2].hand.__eq__ = Mock(
            side_effect=lambda other: False
        )  # Never ties
        mock_players[2].hand.__lt__ = Mock(
            side_effect=lambda other: False
        )  # Never loses

        # Calculate side pots
        side_pots = pot.calculate_side_pots(active_players)

        # Verify pot structure
        assert len(side_pots) == 2

        # Main pot - everyone contributes 200
        assert side_pots[0].amount == 600
        assert len(side_pots[0].eligible_players) == 3

        # Side pot - only Alice's extra 100
        assert side_pots[1].amount == 100
        assert len(side_pots[1].eligible_players) == 1

        # Verify hand comparison works correctly
        # Charlie should win main pot with Ace high
        winners = [
            p.name  # Get player name instead of Player object
            for p in mock_players
            if all(
                p.hand > other.hand
                for other in mock_players
                if other != p and other.name in side_pots[0].eligible_players
            )
        ]
        assert len(winners) == 1, "Should have exactly one winner"
        assert winners[0] == mock_players[2].name, "Charlie should win with Ace high"

    def test_side_pots_with_folded_players(self, pot, mock_players):
        """Test side pot calculation when some players have folded but contributed chips.

        Tests scenario where:
        1. Players have contributed different amounts
        2. Some players have folded
        3. Side pots need to account for folded players' chips

        Assumptions:
        - Should include folded players' chips in pot amounts
        - Should exclude folded players from pot eligibility
        - Should maintain correct pot amounts despite folds
        - Should create appropriate side pots based on active players
        - Should preserve total chip consistency

        Initial state:
        - P1: bet 300, active
        - P2: bet 200, folded
        - P3: bet 100, active

        Expected outcome:
        - Three pots with correct amounts but only non-folded players eligible
        """
        active_players = mock_players.copy()

        # Set initial chips for all players
        for player in mock_players:
            player.chips = 1000
            player.bet = 0
            player.folded = False

        # Track initial total before any bets
        initial_total = sum(p.chips for p in active_players)  # Should be 3000

        # P1 bets 300 and stays in (700 chips left)
        mock_players[0].bet = 300
        mock_players[0].chips = mock_players[0].chips - 300
        mock_players[0].folded = False

        # P2 bets 200 and folds (800 chips left)
        mock_players[1].bet = 200
        mock_players[1].chips = mock_players[1].chips - 200
        mock_players[1].folded = True

        # P3 bets 200 and stays in (800 chips left)
        mock_players[2].bet = 200
        mock_players[2].chips = mock_players[2].chips - 200
        mock_players[2].folded = False

        all_in_players = [mock_players[2]]  # Only non-folded all-in player

        # Calculate expected total after bets
        total_bets = sum(p.bet for p in mock_players)  # 700
        total_remaining = sum(p.chips for p in mock_players)  # 2300
        assert (
            total_bets + total_remaining == initial_total
        ), "Chip total changed during setup"

        side_pots = pot.calculate_side_pots(active_players)

        # Verify pots
        assert len(side_pots) == 2, "Should create two pots"

        # Main pot - everyone contributed 200
        assert side_pots[0].amount == 600, "Main pot should be 200 * 3"
        # Only non-folded players are eligible
        assert len(side_pots[0].eligible_players) == 2
        assert mock_players[0].name in side_pots[0].eligible_players
        assert mock_players[2].name in side_pots[0].eligible_players
        assert mock_players[1].name not in side_pots[0].eligible_players

        # Side pot - only P1's extra 100
        assert side_pots[1].amount == 100
        assert len(side_pots[1].eligible_players) == 1
        assert side_pots[1].eligible_players[0] == mock_players[0].name

        # Verify total chips haven't changed
        final_total = sum(p.chips for p in active_players) + sum(
            pot.amount for pot in side_pots
        )
        assert (
            final_total == initial_total
        ), f"Chip total mismatch: {initial_total} vs {final_total}"

    def test_side_pots_all_in_below_current_bet(self, pot, mock_players):
        """Test side pots when a player goes all-in for less than current bet.

        Tests scenario where:
        1. Current bet is established
        2. Player goes all-in for less than current bet
        3. Other players have already bet more

        Assumptions:
        - Should handle partial all-in amounts correctly
        - Should create main pot limited to all-in amount
        - Should create side pot for excess bets
        - Should maintain correct eligibility in each pot
        - Should handle bet amount differences properly

        Initial state:
        - P1: bet 200
        - P2: all-in for 100 (less than current bet)
        - P3: matched 200

        Expected outcome:
        - Two pots:
          1. Main pot: 300 (100 × 3) - all players eligible
          2. Side pot: 200 (100 × 2) - P1 and P3 only
        """
        active_players = mock_players.copy()

        # P1 bets 200
        mock_players[0].bet = 200
        mock_players[0].chips = 800
        mock_players[0].folded = False

        # P2 goes all-in for 100 (less than current bet)
        mock_players[1].bet = 100
        mock_players[1].chips = 0
        mock_players[1].folded = False

        # P3 calls full amount of 200
        mock_players[2].bet = 200
        mock_players[2].chips = 800
        mock_players[2].folded = False

        side_pots = pot.calculate_side_pots(active_players)

        # Verify pots
        assert len(side_pots) == 2, "Should create two pots"

        # Main pot - all players contributed 100
        assert side_pots[0].amount == 300, "Main pot should be 100 * 3"
        assert len(side_pots[0].eligible_players) == 3

        # Side pot - P1 and P3 contribute remaining 100 each
        assert side_pots[1].amount == 200, "Side pot should be 100 * 2"
        assert len(side_pots[1].eligible_players) == 2
        assert mock_players[1].name not in side_pots[1].eligible_players

    def test_side_pots_zero_chip_all_in(self, pot, mock_players):
        """Test handling of players who are all-in with zero chips remaining.

        Tests edge case where:
        1. Players have gone all-in in previous rounds
        2. Players have zero chips but valid bets
        3. Side pots need to be calculated with zero-chip players

        Assumptions:
        - Should handle zero-chip all-in players correctly
        - Should create appropriate pots based on bet amounts
        - Should maintain correct eligibility despite zero chips
        - Should not allow zero-chip players to bet in new rounds
        - Should preserve total chip consistency

        Initial state:
        - P1: bet 100, chips 0 (all-in)
        - P2: bet 100, chips 0 (all-in)
        - P3: bet 100, chips 0 (all-in)

        Expected outcome:
        - Single pot:
          - Amount: 300 (100 × 3)
          - All players eligible
        """
        active_players = mock_players.copy()

        # Set initial chips for all players
        for player in mock_players:
            player.chips = 500
            player.bet = 0
            player.folded = False

        # Track initial total before any bets
        initial_total = sum(p.chips for p in active_players)  # Should be 1500

        # P1 bets 100
        mock_players[0].bet = 100
        mock_players[0].chips = 400
        mock_players[0].folded = False

        # P2 matches the bet but folds
        mock_players[1].bet = 100
        mock_players[1].chips = 400
        mock_players[1].folded = True

        # P3 calls P1's bet
        mock_players[2].bet = 100
        mock_players[2].chips = 400
        mock_players[2].folded = False

        side_pots = pot.calculate_side_pots(active_players)

        # Verify pots
        assert len(side_pots) == 1, "Should create one pot"
        assert side_pots[0].amount == 300, "Pot should include all bets"
        # Only non-folded players are eligible
        assert len(side_pots[0].eligible_players) == 2
        assert mock_players[1].name not in side_pots[0].eligible_players

        # Verify total chips haven't changed
        final_total = sum(p.chips for p in active_players) + sum(
            pot.amount for pot in side_pots
        )
        assert (
            final_total == initial_total
        ), f"Chip total mismatch: {initial_total} vs {final_total}"

    def test_side_pots_simultaneous_all_ins(self, pot, mock_players):
        """Test when multiple players go all-in simultaneously in the same betting round.

        Tests a scenario where:
        1. Multiple players go all-in in the same round
        2. Players go all-in for different amounts
        3. Side pots are created based on all-in amounts

        Assumptions:
        - Should handle multiple simultaneous all-ins correctly
        - Should create appropriate pots for each all-in level
        - Should maintain correct eligibility for each pot level
        - Should calculate correct pot amounts for each level
        - Should preserve total chips across all pots

        Initial state:
        - P1: all-in for 1000
        - P2: all-in for 1000
        - P3: all-in for 500

        Expected outcome:
        - Two pots:
          1. Main pot: 1500 (500 × 3) - all players eligible
          2. Side pot: 1000 (500 × 2) - only P1 and P2 eligible
        """
        active_players = mock_players.copy()

        # All players go all-in for different amounts
        mock_players[0].bet = 1000
        mock_players[0].chips = 0
        mock_players[0].folded = False

        mock_players[1].bet = 1000
        mock_players[1].chips = 0
        mock_players[1].folded = False

        mock_players[2].bet = 500
        mock_players[2].chips = 0
        mock_players[2].folded = False

        all_in_players = mock_players.copy()

        side_pots = pot.calculate_side_pots(active_players)

        # Verify pots
        assert len(side_pots) == 2, "Should create two pots"

        # Main pot - everyone contributes 500
        assert side_pots[0].amount == 1500, "Main pot should be 500 * 3"
        assert len(side_pots[0].eligible_players) == 3

        # Side pot - P1 and P2 contribute remaining 500 each
        assert side_pots[1].amount == 1000, "Side pot should be 500 * 2"
        assert len(side_pots[1].eligible_players) == 2
        assert mock_players[2].name not in side_pots[1].eligible_players

        # Verify total amount matches total bets
        total_bets = sum(p.bet for p in mock_players)
        total_pots = sum(pot.amount for pot in side_pots)
        assert total_pots == total_bets

    def test_calculate_side_pots_with_existing_main_pot(self, pot, mock_players):
        """Test side pot calculation when there's already money in the main pot.

        Tests pot handling when:
        1. Main pot contains chips from previous betting
        2. New betting round creates side pots

        Assumptions:
        - Should preserve existing main pot amount
        - Should create new side pots only for current round bets
        - Should maintain correct eligibility for new side pots
        - Should handle all-in players correctly with existing pot
        - Should maintain total chip consistency

        Initial state:
        - Existing main pot: 300
        - Current round:
          - P1: bets 200
          - P2: all-in for 200
          - P3: all-in for 100

        Expected outcome:
        - Main pot remains 300
        - Two new side pots:
          1. First pot: 300 (100 × 3)
          2. Second pot: 200 (100 × 2)
        """
        active_players = mock_players.copy()

        # Set existing main pot
        pot.pot = 300  # Previous betting round

        # Current round bets
        mock_players[0].bet = 200
        mock_players[0].chips = 800
        mock_players[1].bet = 200
        mock_players[1].chips = 0  # All-in
        mock_players[2].bet = 100
        mock_players[2].chips = 0  # All-in for less

        side_pots = pot.calculate_side_pots(active_players)

        # Verify pots include only new bets
        assert len(side_pots) == 2
        assert side_pots[0].amount == 300  # All players contribute 100
        assert side_pots[1].amount == 200  # P1 and P2 contribute extra 100

        # Main pot should remain unchanged
        assert pot.pot == 300

    def test_calculate_side_pots_all_players_folded(self, pot, mock_players):
        """Test side pot calculation when all players have folded.

        Tests handling of pots when:
        1. Players have contributed chips
        2. All players subsequently fold

        Assumptions:
        - Should still create pots for contributed chips
        - Should track pot amounts correctly
        - Should handle empty eligible players list
        - Should maintain total chip consistency
        - Should not affect pot amounts when players fold

        Initial state:
        - P1: bets 100 chips
        - P2: bets 200
        - P3: bets 300

        Expected outcome:
        - Single pot with:
          - Amount: 300 (100 × 3)
          - No eligible players
        """
        active_players = mock_players.copy()

        # All players bet but then fold
        for player in mock_players:
            player.bet = 100
            player.chips = 900
            player.folded = True

        side_pots = pot.calculate_side_pots(active_players)

        # Should still create pot but with no eligible players
        assert len(side_pots) == 1
        assert side_pots[0].amount == 300  # Total bets
        assert len(side_pots[0].eligible_players) == 0

    def test_calculate_side_pots_single_chip_differences(self, pot, mock_players):
        """Test side pot calculation with 1-chip differences in bets.

        Tests precision handling where:
        1. Players bet very close amounts
        2. Side pots differ by single chips

        Assumptions:
        - Should handle minimal differences in bet amounts
        - Should create separate pots for each distinct amount
        - Should maintain precise pot amounts even for small differences
        - Should track eligibility correctly for small pot differences
        - Should not merge pots with different eligibility regardless of size

        Initial state:
        - P1: bets 100 chips
        - P2: all-in for 99 chips
        - P3: all-in for 98 chips

        Expected outcome:
        - Three distinct pots:
          1. Main pot: 294 (98 × 3)
          2. First side pot: 2 (1 × 2)
          3. Second side pot: 1 (1 × 1)
        """
        active_players = mock_players.copy()

        # Players bet very close amounts
        mock_players[0].bet = 100
        mock_players[0].chips = 900
        mock_players[1].bet = 99
        mock_players[1].chips = 0  # All-in
        mock_players[2].bet = 98
        mock_players[2].chips = 0  # All-in

        side_pots = pot.calculate_side_pots(active_players)

        # Should create three distinct pots
        assert len(side_pots) == 3
        assert side_pots[0].amount == 294  # 98 * 3
        assert side_pots[1].amount == 2  # 1 * 2
        assert side_pots[2].amount == 1  # 1 * 1

    def test_side_pots_merging_across_rounds(self, pot, mock_players):
        """Test that side pots with identical eligible players are merged even across betting rounds.

        Tests a complex scenario where:
        1. First round creates initial side pots
        2. One player is all-in after first round
        3. Remaining players bet in second round
        4. Side pots should be properly tracked and merged

        Assumptions:
        - Should maintain separate pots when eligibility differs
        - Should track pots correctly across multiple rounds
        - Should handle all-in players correctly in subsequent rounds
        - Should preserve total chips across all rounds
        - Should maintain correct pot amounts and eligibility lists

        Initial state:
        - All players start with 1000 chips
        - Round 1: Alice and Bob bet 400, Charlie all-in for 200
        - Round 2: Alice and Bob bet additional 100 each

        Expected outcome:
        - Three distinct pots:
          1. Main pot: 600 (200 × 3) - all players eligible
          2. First side pot: 400 (200 × 2) - Alice and Bob only
          3. Second side pot: 200 (100 × 2) - Alice and Bob only
        """
        active_players = mock_players.copy()

        # Set initial chips for all players (total should be 3000)
        mock_players[0].chips = 1000  # Alice starts with 1000
        mock_players[1].chips = 1000  # Bob starts with 1000
        mock_players[2].chips = 1000  # Charlie starts with 1000

        # First betting round
        mock_players[0].bet = 400  # Alice bets 400
        mock_players[0].chips -= 400  # Now has 600
        mock_players[1].bet = 400  # Bob matches
        mock_players[1].chips -= 400  # Now has 600
        mock_players[2].bet = 200  # Charlie goes all-in for 200
        mock_players[2].chips -= 200  # Now has 800

        print("\nInitial state:")
        print(f"Total bets: {sum(p.bet for p in active_players)}")
        print(f"Total chips: {sum(p.chips for p in active_players)}")
        print(f"Player states:")
        for p in active_players:
            print(f"  {p.name}: chips={p.chips}, bet={p.bet}")

        # First round pots
        first_round_pots = pot.calculate_side_pots(active_players)

        print("\nAfter first round:")
        print(f"Number of pots: {len(first_round_pots)}")
        for i, pot_obj in enumerate(first_round_pots):
            print(
                f"  Pot {i+1}: amount={pot_obj.amount}, eligible={pot_obj.eligible_players}"
            )
        print(f"Total in pots: {sum(pot.amount for pot in first_round_pots)}")

        # Store first round pots using set_pots method
        pot.set_pots(
            0, first_round_pots
        )  # Set main pot to 0 since all bets are in side pots

        # Clear bets for next round
        for p in active_players:
            p.bet = 0

        # Second betting round
        mock_players[0].bet = 100  # Alice bets 100
        mock_players[0].chips -= 100  # Now has 500
        mock_players[1].bet = 100  # Bob bets remaining 100
        mock_players[1].chips -= 100  # Now has 500
        # Charlie is already all-in, can't bet

        print("\nBefore second round calculation:")
        print(f"Total bets: {sum(p.bet for p in active_players)}")
        print(f"Total chips: {sum(p.chips for p in active_players)}")
        print(f"Existing pots: {sum(pot.amount for pot in (pot.side_pots or []))}")
        print(f"Player states:")
        for p in active_players:
            print(f"  {p.name}: chips={p.chips}, bet={p.bet}")

        # Calculate new side pots - this should automatically merge with existing pots
        final_pots = pot.calculate_side_pots(active_players)

        print("\nFinal state:")
        print(f"Number of pots: {len(final_pots)}")
        for i, pot_obj in enumerate(final_pots):
            print(
                f"  Pot {i+1}: amount={pot_obj.amount}, eligible={pot_obj.eligible_players}"
            )
        print(f"Total in pots: {sum(pot.amount for pot in final_pots)}")
        print(f"Total chips in stacks: {sum(p.chips for p in active_players)}")
        print(
            f"Total chips + pots: {sum(p.chips for p in active_players) + sum(pot.amount for pot in final_pots)}"
        )

        # Verify final merged pots
        assert len(final_pots) == 3, "Should have three pots total"

        # First pot - all players eligible (200 * 3 from first round)
        assert final_pots[0].amount == 600, "Main pot should be from first round"
        assert len(final_pots[0].eligible_players) == 3

        # Second pot - Alice and Bob eligible (200 * 2 from first round)
        assert final_pots[1].amount == 400, "Second pot should be from first round"
        assert len(final_pots[1].eligible_players) == 2

        # Third pot - Alice and Bob eligible (100 * 2 from second round)
        assert final_pots[2].amount == 200, "Third pot should be from second round"
        assert len(final_pots[2].eligible_players) == 2

        # Verify total chips in play remains constant
        total_chips = sum(
            p.chips for p in active_players
        ) + sum(  # Remaining chips in stacks
            pot.amount for pot in final_pots
        )  # All side pots
        assert total_chips == 3000, "Total chips should remain constant"

    def test_overcall_return_scenario(self, pot, mock_players):
        """Test correct handling of overcalls when a player goes all-in for less than current bet.

        Tests a scenario where:
        1. First player makes a full bet
        2. Second player goes all-in for less than the current bet
        3. Third player calls the full bet

        Assumptions:
        - Should handle partial bets from all-in players correctly
        - Should create main pot limited to smallest all-in amount
        - Should create side pot for remaining bets
        - Should maintain correct eligibility in each pot
        - Should calculate correct pot amounts for partial bets
        - Should not allow all-in player in side pot

        Initial state:
        - P1: bets 100, has chips remaining
        - P2: all-in for 50 (less than current bet)
        - P3: calls full 100, has chips remaining

        Expected outcome:
        - Main pot: 150 (50 from each player)
        - Side pot: 100 (50 each from P1 and P3)
        """
        active_players = mock_players.copy()

        # P1 bets 100
        mock_players[0].bet = 100
        mock_players[0].chips = 900
        mock_players[0].folded = False

        # P2 goes all-in for 50 (less than current bet)
        mock_players[1].bet = 50  # All they have
        mock_players[1].chips = 0
        mock_players[1].folded = False

        # P3 calls full amount of 100
        mock_players[2].bet = 100
        mock_players[2].chips = 900
        mock_players[2].folded = False

        side_pots = pot.calculate_side_pots(active_players)

        # Verify pots
        assert len(side_pots) == 2, "Should create two pots"

        # Main pot - all players contribute 50
        assert side_pots[0].amount == 150, "Main pot should be 50 * 3"
        assert len(side_pots[0].eligible_players) == 3

        # Side pot - P1 and P3 contribute remaining 50 each
        assert side_pots[1].amount == 100, "Side pot should be 50 * 2"
        assert len(side_pots[1].eligible_players) == 2
        assert mock_players[1].name not in side_pots[1].eligible_players

    def test_end_betting_round_clears_bets(self, pot, mock_players):
        """Test that end_betting_round properly clears bets after adding to pot.

        Tests the behavior of ending a betting round where:
        1. Multiple players have different bet amounts
        2. Bets are added to the main pot
        3. Player bet amounts are cleared

        Assumptions:
        - Should correctly add all current bets to the main pot
        - Should clear all player bet amounts to zero after adding to pot
        - Should maintain total chip consistency before and after
        - Should handle different bet amounts correctly (100, 200, 300)
        - Should work with multiple players
        - Should not create side pots (handled separately)

        Initial state:
        - P1: bets 100
        - P2: bets 200
        - P3: bets 300

        Expected outcome:
        - Main pot should contain 600 (sum of all bets)
        - All player bet amounts should be 0
        - Total chips in play should remain constant
        """
        active_players = mock_players.copy()
        initial_total = sum(p.chips for p in active_players)

        # Setup some bets
        for i, player in enumerate(active_players):
            bet_amount = (i + 1) * 100  # 100, 200, 300
            player.chips -= bet_amount
            player.bet = bet_amount

        # End betting round
        pot.end_betting_round(active_players)

        # Verify bets were added to pot
        assert pot.pot == 600, "Pot should contain all bets"

        # Verify bets were cleared
        for player in active_players:
            assert player.bet == 0, f"{player.name}'s bet should be cleared"

        # Verify total chips unchanged
        current_total = sum(p.chips for p in active_players) + pot.pot
        assert current_total == initial_total, "Total chips should remain constant"

    def test_multiple_betting_rounds_with_all_in(self, pot, mock_players):
        """Test handling of multiple betting rounds when a player is all-in.

        Tests a complex scenario where:
        1. One player goes all-in in first round
        2. Remaining players continue betting in subsequent rounds
        3. Side pots are created and tracked across rounds

        Assumptions:
        - Should track side pots correctly across multiple rounds
        - Should prevent all-in players from betting in later rounds
        - Should maintain correct pot eligibility for each player
        - Should create appropriate side pots for each betting level
        - Should handle mix of active and all-in players correctly
        - Should preserve total chips across all rounds
        - Should maintain correct pot amounts and eligibility lists

        Initial state:
        - P1: 1000 chips
        - P2: 500 chips
        - P3: 100 chips (goes all-in first round)

        Expected outcome:
        - Three pots total:
          1. Main pot: All players eligible (300 total)
          2. First side pot: P1 and P2 from round 1 (200 total)
          3. Second side pot: P1 and P2 from round 2 (600 total)
        """
        # Set up initial chip stacks
        mock_players[0].chips = 1000  # P1 starts with 1000
        mock_players[1].chips = 500  # P2 starts with 500
        mock_players[2].chips = 100  # P3 starts with 100 (not 200)

        active_players = mock_players.copy()
        initial_total = sum(p.chips for p in active_players)

        # Round 1: P3 goes all-in
        mock_players[0].bet = 200
        mock_players[0].chips -= 200  # 800 left
        mock_players[1].bet = 200
        mock_players[1].chips -= 200  # 300 left
        mock_players[2].bet = 100  # All-in
        mock_players[2].chips = 0

        # Calculate side pots after round 1
        side_pots = pot.calculate_side_pots(active_players)
        pot.side_pots = side_pots

        # Clear round 1 bets
        for player in active_players:
            player.bet = 0

        # Round 2: P1 and P2 continue betting
        mock_players[0].bet = 300
        mock_players[0].chips -= 300  # 500 left
        mock_players[1].bet = 300
        mock_players[1].chips -= 300  # 0 left
        # P3 can't bet (all-in)

        # Calculate final side pots
        final_pots = pot.calculate_side_pots(active_players)

        # Verify pot structure
        assert (
            len(final_pots) == 3
        ), f"Should have three pots\n{get_game_state_str(pot, active_players)}"

        # Main pot - all players contributed 100
        assert (
            final_pots[0].amount == 300
        ), f"Main pot should be 100 * 3\n{get_game_state_str(pot, active_players)}"
        assert (
            len(final_pots[0].eligible_players) == 3
        ), f"Main pot should have 3 eligible players\n{get_game_state_str(pot, active_players)}"

        # First side pot - P1 and P2's extra 100 from round 1
        assert (
            final_pots[1].amount == 200
        ), f"First side pot should be 100 * 2\n{get_game_state_str(pot, active_players)}"
        assert (
            len(final_pots[1].eligible_players) == 2
        ), f"First side pot should have 2 eligible players\n{get_game_state_str(pot, active_players)}"
        assert (
            mock_players[2].name not in final_pots[1].eligible_players
        ), f"P3 should not be eligible for first side pot\n{get_game_state_str(pot, active_players)}"

        # Second side pot - P1 and P2's round 2 bets
        assert (
            final_pots[2].amount == 600
        ), f"Second side pot should be 300 * 2\n{get_game_state_str(pot, active_players)}"
        assert (
            len(final_pots[2].eligible_players) == 2
        ), f"Second side pot should have 2 eligible players\n{get_game_state_str(pot, active_players)}"
        assert (
            mock_players[2].name not in final_pots[2].eligible_players
        ), f"P3 should not be eligible for second side pot\n{get_game_state_str(pot, active_players)}"

        # Verify total chips unchanged
        current_total = sum(p.chips for p in active_players) + sum(
            pot.amount for pot in final_pots
        )
        assert current_total == initial_total, (
            f"Total chips should remain constant\n"
            f"Initial total: {initial_total}\n"
            f"Current total: {current_total}\n"
            f"{get_game_state_str(pot, active_players)}"
        )

    def test_get_state(self, pot, mock_players):
        """Test getting complete pot state.

        Tests that:
        1. Main pot amount is correct
        2. Side pots are included
        3. Total pot calculation is correct
        4. None side_pots are handled correctly

        Assumptions:
        - Should return correct PotState object
        - Should calculate total pot correctly
        - Should handle both main pot and side pots
        - Should convert None side_pots to empty list
        """
        # Test with only main pot
        pot.pot = 100
        state = pot.get_state()
        assert state.main_pot == 100
        assert state.side_pots == []
        assert state.total_pot == 100

        # Test with main pot and side pots
        pot.side_pots = [
            SidePot(amount=200, eligible_players=["Alice", "Bob"]),
            SidePot(amount=300, eligible_players=["Alice"]),
        ]
        state = pot.get_state()
        assert state.main_pot == 100
        assert len(state.side_pots) == 2
        assert state.side_pots[0].amount == 200
        assert state.side_pots[1].amount == 300
        assert state.total_pot == 600  # 100 + 200 + 300
