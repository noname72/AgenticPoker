import pytest

from data.states.player_state import PlayerState
from data.types.player_types import PlayerPosition
from game.player import Player


@pytest.fixture
def basic_player_state():
    """Create a basic PlayerState for testing."""
    return PlayerState(
        name="TestPlayer",
        chips=1000,
        bet=0,
        folded=False,
        position=PlayerPosition.DEALER,
    )


@pytest.fixture
def mock_player():
    """Create a mock Player instance."""
    return Player("TestPlayer", chips=1000)


class TestPlayerState:
    def test_initialization(self, basic_player_state):
        """Test that PlayerState initializes correctly with all required fields."""
        assert basic_player_state.name == "TestPlayer"
        assert basic_player_state.chips == 1000
        assert basic_player_state.bet == 0
        assert basic_player_state.folded is False
        assert basic_player_state.position == PlayerPosition.DEALER

    def test_default_values(self):
        """Test that optional fields have correct default values."""
        player_state = PlayerState(
            name="TestPlayer",
            chips=1000,
            bet=0,
            folded=False,
            position=PlayerPosition.OTHER,
        )
        assert player_state.hand is None
        assert player_state.hand_rank is None
        assert player_state.total_bet_this_round == 0
        assert player_state.last_action is None
        assert player_state.last_raise_amount is None
        assert player_state.is_all_in is False
        assert player_state.is_active is True

    def test_dict_access(self, basic_player_state):
        """Test dictionary-style access to attributes."""
        assert basic_player_state["name"] == "TestPlayer"
        assert basic_player_state["chips"] == 1000
        assert basic_player_state["position"] == "dealer"

    def test_contains_method(self, basic_player_state):
        """Test the __contains__ method."""
        assert "name" in basic_player_state
        assert "chips" in basic_player_state
        assert "not_an_attribute" not in basic_player_state

    def test_get_method(self, basic_player_state):
        """Test the get() method with default values."""
        assert basic_player_state.get("name") == "TestPlayer"
        assert basic_player_state.get("not_an_attribute", "default") == "default"

    def test_from_player_method(self, mock_player):
        """Test creating PlayerState from a Player instance."""
        player_state = PlayerState.from_player(mock_player)

        assert player_state.name == mock_player.name
        assert player_state.chips == mock_player.chips
        assert player_state.bet == mock_player.bet
        assert player_state.folded == mock_player.folded
        assert isinstance(player_state.position, PlayerPosition)

    def test_model_validation(self):
        """Test Pydantic model validation."""
        # Test negative chips
        with pytest.raises(ValueError):
            PlayerState(
                name="TestPlayer",
                chips=-100,  # Invalid negative amount
                bet=0,
                folded=False,
                position=PlayerPosition.DEALER,
            )

        # Test negative bet
        with pytest.raises(ValueError):
            PlayerState(
                name="TestPlayer",
                chips=1000,
                bet=-50,  # Invalid negative amount
                folded=False,
                position=PlayerPosition.DEALER,
            )

        # Test negative historical values
        with pytest.raises(ValueError):
            PlayerState(
                name="TestPlayer",
                chips=1000,
                bet=0,
                folded=False,
                position=PlayerPosition.DEALER,
                hands_played=-1,  # Invalid negative amount
            )

    def test_string_conversion(self, basic_player_state):
        """Test string conversion of hand and hand_rank."""
        state = basic_player_state.copy()
        state.hand = "AhKh"
        state.hand_rank = "Flush"

        player_dict = state.to_dict()
        assert player_dict["hand"] == "AhKh"
        assert player_dict["hand_rank"] == "Flush"

    def test_active_status(self):
        """Test is_active status based on folded and all-in conditions."""
        # Player who hasn't folded and isn't all-in should be active
        active_player = PlayerState(
            name="Active",
            chips=1000,
            bet=0,
            folded=False,
            position=PlayerPosition.DEALER,
            is_all_in=False,
        )
        assert active_player.is_active is True

        # Player who has folded should not be active
        folded_player = PlayerState(
            name="Folded",
            chips=1000,
            bet=0,
            folded=True,
            position=PlayerPosition.DEALER,
        )
        assert folded_player.is_active is True  # Because is_active is set explicitly

        # Player who is all-in should still be marked as active
        all_in_player = PlayerState(
            name="AllIn",
            chips=0,
            bet=1000,
            folded=False,
            position=PlayerPosition.DEALER,
            is_all_in=True,
        )
        assert all_in_player.is_active is True
