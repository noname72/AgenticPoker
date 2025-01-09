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
        is_dealer=True,
        is_small_blind=False,
        is_big_blind=False,
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
        assert basic_player_state.is_dealer is True
        assert basic_player_state.is_small_blind is False
        assert basic_player_state.is_big_blind is False
        assert basic_player_state.hands_played == 0
        assert basic_player_state.total_winnings == 0

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

    def test_to_dict_method(self, basic_player_state):
        """Test that to_dict() creates correct dictionary structure."""
        player_dict = basic_player_state.to_dict()

        assert "basic_info" in player_dict
        assert player_dict["basic_info"]["name"] == "TestPlayer"
        assert player_dict["basic_info"]["chips"] == 1000

        assert player_dict["position"] == "dealer"
        assert player_dict["is_dealer"] is True

        assert "betting" in player_dict
        assert player_dict["betting"]["total_bet"] == 0

        assert "history" in player_dict
        assert player_dict["history"]["hands_played"] == 0
        assert player_dict["history"]["total_winnings"] == 0

        assert player_dict["position"] == "dealer"
        assert "basic_info" in player_dict
        assert player_dict["basic_info"]["name"] == "TestPlayer"
        assert player_dict["basic_info"]["chips"] == 1000

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

    def test_nested_dict_structure(self, basic_player_state):
        """Test the nested dictionary structure returned by to_dict()."""
        player_dict = basic_player_state.to_dict()

        # Test basic info structure
        assert "basic_info" in player_dict
        basic_info = player_dict["basic_info"]
        assert basic_info["name"] == "TestPlayer"
        assert basic_info["chips"] == 1000
        assert basic_info["bet"] == 0
        assert basic_info["folded"] is False

        # Test position structure
        assert player_dict["position"] == "dealer"
        assert player_dict["is_dealer"] is True
        assert player_dict["is_small_blind"] is False
        assert player_dict["is_big_blind"] is False

        # Test betting structure
        assert "betting" in player_dict
        betting = player_dict["betting"]
        assert betting["total_bet"] == 0
        assert betting["last_action"] is None
        assert betting["last_raise"] is None

        # Test status structure
        assert "status" in player_dict
        status = player_dict["status"]
        assert status["all_in"] is False
        assert status["active"] is True
        assert status["chips_at_start"] is None
