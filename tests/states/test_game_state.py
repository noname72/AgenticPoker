import pytest

from data.states.game_state import GameState
from data.types.base_types import DeckState
from data.states.player_state import PlayerState
from data.types.player_types import PlayerPosition
from data.types.pot_types import PotState
from data.states.round_state import RoundState
from game.game import AgenticPoker
from game.player import Player

@pytest.fixture
def basic_game_state():
    """Create a basic GameState for testing."""
    return GameState(
        players=[
            PlayerState(
                name="Player1",
                chips=1000,
                position=PlayerPosition.DEALER,
                bet=0,
                folded=False,
                is_all_in=False,
                checked=False,
                called=False,
            )
        ],
        dealer_position=0,
        small_blind=10,
        big_blind=20,
        ante=0,
        min_bet=20,
        round_state=RoundState(
            phase="pre_draw",
            current_bet=20,
            round_number=1,
            dealer_position=0,
            small_blind_position=1,
            big_blind_position=2,
            first_bettor_index=3,
        ),
        pot_state=PotState(main_pot=0),
        deck_state=DeckState(cards_remaining=52),
    )


@pytest.fixture
def mock_game():
    """Create a mock game instance."""
    # Create Player objects with initial chips
    players = [Player("Player1", chips=1000), Player("Player2", chips=1000)]

    game = AgenticPoker(players, small_blind=10, big_blind=20)
    return game


class TestGameState:
    def test_initialization(self, basic_game_state):
        """Test that GameState initializes correctly with all required fields."""
        assert basic_game_state.small_blind == 10
        assert basic_game_state.big_blind == 20
        assert basic_game_state.ante == 0
        assert basic_game_state.min_bet == 20
        assert basic_game_state.max_raise_multiplier == 3
        assert basic_game_state.max_raises_per_round == 4
        assert len(basic_game_state.players) == 1
        assert basic_game_state.dealer_position == 0
        assert basic_game_state.active_player_position is None

    def test_copy_method(self, basic_game_state):
        """Test that copy() creates a deep copy."""
        copied = basic_game_state.copy()

        # Verify it's a different object
        assert copied is not basic_game_state

        # Verify all attributes are equal
        assert copied.small_blind == basic_game_state.small_blind
        assert copied.big_blind == basic_game_state.big_blind
        assert copied.players[0].name == basic_game_state.players[0].name

        # Verify it's a deep copy
        copied.players[0].chips = 500
        assert basic_game_state.players[0].chips == 1000

    def test_to_dict_method(self, basic_game_state):
        """Test that to_dict() creates correct dictionary structure."""
        game_dict = basic_game_state.to_dict()

        assert "config" in game_dict
        assert game_dict["config"]["small_blind"] == 10
        assert game_dict["config"]["big_blind"] == 20

        assert "players" in game_dict
        assert len(game_dict["players"]) == 1

        assert "positions" in game_dict
        assert game_dict["positions"]["dealer"] == 0

        assert "pot" in game_dict
        assert "current_bet" in game_dict

    def test_dict_access(self, basic_game_state):
        """Test dictionary-style access to attributes."""
        assert basic_game_state["small_blind"] == 10
        assert basic_game_state["big_blind"] == 20
        assert basic_game_state["dealer_position"] == 0

    def test_contains_method(self, basic_game_state):
        """Test the __contains__ method."""
        assert "small_blind" in basic_game_state
        assert "big_blind" in basic_game_state
        assert "not_an_attribute" not in basic_game_state

    def test_get_method(self, basic_game_state):
        """Test the get() method with default values."""
        assert basic_game_state.get("small_blind") == 10
        assert basic_game_state.get("not_an_attribute", "default") == "default"

    def test_from_game_method(self, mock_game):
        """Test creating GameState from a Game instance."""
        game_state = GameState.from_game(mock_game)

        # Verify basic attributes
        assert game_state.small_blind == mock_game.small_blind
        assert game_state.big_blind == mock_game.big_blind
        assert game_state.dealer_position == mock_game.dealer_index

        # Verify player states and positions
        assert len(game_state.players) == len(mock_game.table)
        for player_state, game_player in zip(game_state.players, mock_game.table):
            assert player_state.name == game_player.name
            assert player_state.chips == game_player.chips

        # Verify round state positions
        players_count = len(mock_game.table)
        expected_sb_pos = (mock_game.dealer_index + 1) % players_count
        expected_bb_pos = (mock_game.dealer_index + 2) % players_count
        expected_first_bettor = (expected_bb_pos + 1) % players_count

        assert game_state.round_state.dealer_position == mock_game.dealer_index
        assert game_state.round_state.small_blind_position == expected_sb_pos
        assert game_state.round_state.big_blind_position == expected_bb_pos
        assert game_state.round_state.first_bettor_index == expected_first_bettor

    def test_position_assignments(self, mock_game):
        """Test that player positions are correctly assigned relative to dealer."""
        game_state = GameState.from_game(mock_game)

        # With 2 players, positions should be Dealer and Big Blind
        assert (
            game_state.players[mock_game.dealer_index].position == PlayerPosition.DEALER
        )
        next_pos = (mock_game.dealer_index + 1) % len(mock_game.table)
        assert game_state.players[next_pos].position == PlayerPosition.SMALL_BLIND

    def test_model_validation(self):
        """Test Pydantic model validation."""
        # Test negative chips
        with pytest.raises(ValueError, match="Amount cannot be negative"):
            GameState(
                players=[
                    PlayerState(
                        name="Player1",
                        chips=1000,
                        position=PlayerPosition.DEALER,
                        bet=0,
                        folded=False,
                        is_all_in=False,
                        checked=False,
                        called=False,
                    )
                ],
                dealer_position=0,
                small_blind=-10,  # Invalid negative amount
                big_blind=20,
                ante=0,
                min_bet=20,
                round_state=RoundState(
                    phase="pre_draw",
                    current_bet=20,
                    round_number=1,
                    dealer_position=0,
                    small_blind_position=1,
                    big_blind_position=2,
                    first_bettor_index=3,
                ),
                pot_state=PotState(main_pot=0),
                deck_state=DeckState(cards_remaining=52),
            )
