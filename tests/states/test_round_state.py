import pytest

from data.states.round_state import RoundPhase, RoundState


@pytest.fixture
def basic_round_state():
    """Create a basic RoundState for testing."""
    return RoundState(
        phase=RoundPhase.PREFLOP,
        current_bet=20,
        round_number=1,
        dealer_position=0,
        small_blind_position=1,
        big_blind_position=2,
    )


class TestRoundState:
    def test_initialization(self, basic_round_state):
        """Test that RoundState initializes correctly with all required fields."""
        assert basic_round_state.phase == RoundPhase.PREFLOP
        assert basic_round_state.current_bet == 20
        assert basic_round_state.round_number == 1
        assert basic_round_state.raise_count == 0
        assert basic_round_state.dealer_position == 0
        assert basic_round_state.small_blind_position == 1
        assert basic_round_state.big_blind_position == 2
        assert basic_round_state.main_pot == 0
        assert basic_round_state.side_pots == []
        assert basic_round_state.last_raiser is None
        assert basic_round_state.last_aggressor is None
        assert basic_round_state.needs_to_act == []
        assert basic_round_state.acted_this_phase == []
        assert basic_round_state.is_complete is False
        assert basic_round_state.winner is None

    def test_new_round_factory_method(self):
        """Test the new_round class method."""
        round_state = RoundState.new_round(round_number=1)
        assert round_state.phase == RoundPhase.PREFLOP
        assert round_state.current_bet == 0
        assert round_state.round_number == 1
        assert round_state.raise_count == 0
        assert round_state.dealer_position is None
        assert round_state.main_pot == 0
        assert round_state.side_pots == []

    def test_round_phase_enum(self):
        """Test RoundPhase enum values."""
        assert RoundPhase.PREFLOP == "preflop"
        assert RoundPhase.FLOP == "flop"
        assert RoundPhase.TURN == "turn"
        assert RoundPhase.RIVER == "river"
        assert RoundPhase.SHOWDOWN == "showdown"
        assert RoundPhase.PRE_DRAW == "pre_draw"
        assert RoundPhase.POST_DRAW == "post_draw"

    def test_model_validation(self):
        """Test Pydantic model validation."""
        # Test negative current bet
        with pytest.raises(ValueError):
            RoundState(
                phase=RoundPhase.PREFLOP,
                current_bet=-20,  # Invalid negative amount
                round_number=1,
            )

        # Test negative round number
        with pytest.raises(ValueError):
            RoundState(
                phase=RoundPhase.PREFLOP,
                current_bet=20,
                round_number=-1,  # Invalid negative round number
            )

        # Test negative raise count
        with pytest.raises(ValueError):
            RoundState(
                phase=RoundPhase.PREFLOP,
                current_bet=20,
                round_number=1,
                raise_count=-1,  # Invalid negative raise count
            )

    def test_betting_tracking(self):
        """Test tracking of betting actions."""
        round_state = basic_round_state

        # Test adding players who need to act
        round_state.needs_to_act = ["Player1", "Player2"]
        assert "Player1" in round_state.needs_to_act
        assert "Player2" in round_state.needs_to_act

        # Test tracking acted players
        round_state.acted_this_phase = ["Player1"]
        assert "Player1" in round_state.acted_this_phase
        assert "Player2" not in round_state.acted_this_phase

        # Test setting last raiser
        round_state.last_raiser = "Player1"
        assert round_state.last_raiser == "Player1"

        # Test setting last aggressor
        round_state.last_aggressor = "Player2"
        assert round_state.last_aggressor == "Player2"

    def test_pot_management(self):
        """Test pot management functionality."""
        round_state = basic_round_state
        
        # Test main pot
        round_state.main_pot = 100
        assert round_state.main_pot == 100

        # Test side pots
        # Initialize side_pots as empty list first
        round_state.side_pots = []
        side_pot = {"amount": 50, "players": ["Player1", "Player2"]}
        round_state.side_pots.append(side_pot)
        assert len(round_state.side_pots) == 1
        assert round_state.side_pots[0]["amount"] == 50
        assert round_state.side_pots[0]["players"] == ["Player1", "Player2"]

    def test_round_completion(self):
        """Test round completion functionality."""
        round_state = basic_round_state

        # Test marking round as complete
        round_state.is_complete = True
        assert round_state.is_complete

        # Test setting winner
        round_state.winner = "Player1"
        assert round_state.winner == "Player1"
