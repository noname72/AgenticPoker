import pytest
from pydantic import ValidationError

from data.states.player_state import PlayerState
from data.types.player_types import PlayerPosition
from game.player import Player
from game.hand import Hand

# Update PlayerState's forward refs at module level
PlayerState.update_forward_refs(Hand=Hand)


@pytest.fixture
def basic_player_state():
    """Create a basic PlayerState for testing."""
    return PlayerState(
        name="TestPlayer",
        chips=1000,
        bet=0,
        folded=False,
        position=PlayerPosition.DEALER,
        is_all_in=False,
        checked=False,
        called=False,
    )


@pytest.fixture
def mock_player():
    """Create a mock Player instance."""
    return Player(
        "TestPlayer",
        chips=1000,
    )


class TestPlayerState:
    def test_initialization(self, basic_player_state):
        """Test that PlayerState initializes correctly with all required fields."""
        assert basic_player_state.name == "TestPlayer"
        assert basic_player_state.chips == 1000
        assert basic_player_state.bet == 0
        assert basic_player_state.folded is False
        assert basic_player_state.position == PlayerPosition.DEALER
        assert basic_player_state.is_all_in is False
        assert basic_player_state.checked is False
        assert basic_player_state.called is False

    def test_default_values(self):
        """Test that optional fields have correct default values."""
        player_state = PlayerState(
            name="TestPlayer",
            chips=1000,
            bet=0,
            folded=False,
            position=PlayerPosition.OTHER,
            is_all_in=False,
            checked=False,
            called=False,
        )
        assert player_state.hand is None
        assert not player_state.is_all_in
        assert not player_state.checked
        assert not player_state.called

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
        assert not player_state.is_all_in
        assert not player_state.checked
        assert not player_state.called

    def test_model_validation(self):
        """Test Pydantic model validation."""
        # Test negative chips
        with pytest.raises(ValidationError) as exc_info:
            PlayerState(
                name="TestPlayer",
                chips=-100,  # Invalid negative amount
                bet=0,
                folded=False,
                position=PlayerPosition.DEALER,
                is_all_in=False,
                checked=False,
                called=False,
            )
        assert "ensure this value is greater than or equal to 0" in str(exc_info.value)

        # Test negative bet
        with pytest.raises(ValidationError) as exc_info:
            PlayerState(
                name="TestPlayer",
                chips=1000,
                bet=-50,  # Invalid negative amount
                folded=False,
                position=PlayerPosition.DEALER,
                is_all_in=False,
                checked=False,
                called=False,
            )
        assert "ensure this value is greater than or equal to 0" in str(exc_info.value)

    def test_string_conversion(self, basic_player_state):
        """Test string conversion of hand."""
        state = basic_player_state.copy()
        state.hand = "AhKh"  # Assuming Hand can be set as a string for testing

        player_dict = state.to_dict()
        assert player_dict["hand"] == "AhKh"

    def test_active_status_with_all_fields(self):
        """Test various combinations of player states."""
        # Basic active player
        active_player = PlayerState(
            name="Active",
            chips=1000,
            bet=0,
            folded=False,
            position=PlayerPosition.DEALER,
            is_all_in=False,
            checked=False,
            called=False,
        )
        assert active_player.is_all_in is False
        assert active_player.checked is False
        assert active_player.called is False

        # All-in player
        all_in_player = PlayerState(
            name="AllIn",
            chips=0,
            bet=1000,
            folded=False,
            position=PlayerPosition.DEALER,
            is_all_in=True,
            checked=False,
            called=False,
        )
        assert all_in_player.is_all_in is True

        # Player who has checked
        checked_player = PlayerState(
            name="Checked",
            chips=1000,
            bet=0,
            folded=False,
            position=PlayerPosition.DEALER,
            is_all_in=False,
            checked=True,
            called=False,
        )
        assert checked_player.checked is True

        # Player who has called
        called_player = PlayerState(
            name="Called",
            chips=800,
            bet=200,
            folded=False,
            position=PlayerPosition.DEALER,
            is_all_in=False,
            checked=False,
            called=True,
        )
        assert called_player.called is True
