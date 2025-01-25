from unittest.mock import MagicMock

from data.states.player_state import PlayerState
from data.states.round_state import RoundPhase
from data.types.player_types import PlayerPosition
from game.player import Player
from tests.mocks.mock_hand import MockHand


class MockPlayer(Player):
    """A mock implementation of the Player class for testing purposes.

    This mock provides the same interface as the real Player class but with configurable
    behaviors for testing. It tracks player state (chips, bets, etc.) and allows easy
    configuration of player actions and responses.

    Usage:
        # Basic initialization
        player = MockPlayer(name="TestPlayer", chips=1000)

        # Configure specific actions
        player.place_bet.return_value = 50  # Configure bet amount
        player.is_all_in = True  # Set player state
        player.folded = False

        # Configure hand ranking
        player.hand.set_rank(1, [14, 13, 12, 11, 10], "Royal Flush")

        # Configure action responses
        player.execute.side_effect = lambda action, game: None

        # Test player state
        assert player.chips == 1000
        assert player.bet == 0

        # Verify method calls
        player.place_bet.assert_called_with(50, game_mock)
        player.execute.assert_called_once()

    Default Behaviors:
        - place_bet: Returns configured bet amount or 0 by default
        - execute: Handles RAISE, CALL, CHECK, FOLD actions
        - reset_bet: Resets bet amount to 0
        - reset_for_new_round: Resets all player state for new round
        - get_state: Returns current PlayerState

    Attributes:
        name (str): Player's name
        chips (int): Current chip count
        bet (int): Current bet amount
        folded (bool): Whether player has folded
        hand (MockHand): Player's current hand (mockable)
        position (PlayerPosition): Player's position
        is_all_in (bool): Whether player is all-in
        checked (bool): Whether player has checked
        called (bool): Whether player has called

    All methods are MagicMocks that can be configured with custom return values
    or side effects as needed for testing.
    """

    def __init__(self, name: str = "TestPlayer", chips: int = 1000):
        """Initialize mock player with configurable parameters."""
        # Call parent class constructor first
        super().__init__(name=name, chips=chips)

        # Initialize mock methods that can be configured in tests
        self.place_bet = MagicMock(side_effect=self._default_place_bet)
        self.execute = MagicMock()
        self._raise = MagicMock()
        self._call = MagicMock()
        self._check = MagicMock()
        self._fold = MagicMock()
        self.reset_bet = MagicMock()
        self.reset_for_new_round = MagicMock()
        self.decide_action = MagicMock()

        # Initialize other attributes
        self.hand = MockHand()
        self._position = PlayerPosition.OTHER
        self.is_all_in = False
        self.checked = False
        self.called = False
        self.total_bet_this_round = 0
        self.last_action = None
        self.last_raise_amount = None
        self.is_dealer = False
        self.is_small_blind = False
        self.is_big_blind = False
        self.chips_at_start_of_hand = chips

    @property
    def position(self) -> PlayerPosition:
        """Get the player's current position at the table."""
        return self._position

    @position.setter
    def position(self, value: PlayerPosition):
        """Set the player's position at the table."""
        self._position = value

    def get_state(self) -> PlayerState:
        """Get the current state of this player."""
        return PlayerState.from_player(self)

    def __eq__(self, other):
        """Compare players based on their name and state.

        Two players are considered equal if they have:
        - Same name
        - Same chip count
        - Same folded state
        - Same all-in state
        - Same bet amount
        """
        if not isinstance(other, MockPlayer):
            return False
        return (
            self.name == other.name
            and self.chips == other.chips
            and self.folded == other.folded
            and self.is_all_in == other.is_all_in
            and self.bet == other.bet
        )

    def __repr__(self):
        """Provide readable string representation for debugging."""
        return f"MockPlayer(name='{self.name}', chips={self.chips}, folded={self.folded}, all_in={self.is_all_in})"

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return f"{self.name} (chips: {self.chips}, folded: {self.folded})"

    def _default_place_bet(self, amount: int, game) -> int:
        """Default behavior for placing bets that mimics real Player behavior."""
        if amount < 0:
            raise ValueError("Cannot place negative bet")

        # Ensure we don't bet more than available chips
        amount = min(amount, self.chips)

        # Track the bet and reduce chips
        self.chips -= amount
        self.bet += amount

        # Add the bet to the pot if game has pot
        if hasattr(game, "pot"):
            game.pot.pot += amount

        return amount
