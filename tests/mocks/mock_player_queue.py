from typing import List, Optional
from unittest.mock import MagicMock

from tests.mocks.mock_player import MockPlayer


class MockPlayerQueue:
    """A mock implementation of the PlayerQueue class for testing purposes.

    This mock provides the same interface as the real PlayerQueue but with configurable
    behaviors for testing. It manages a circular queue of mock players and allows easy
    configuration of player rotation and round state.

    Usage:
        # Basic initialization with mock players
        players = [
            MockPlayer("Player1", chips=1000),
            MockPlayer("Player2", chips=1000),
            MockPlayer("Player3", chips=1000)
        ]
        queue = MockPlayerQueue(players)

        # Configure specific behaviors
        queue.configure_for_test(
            players=players,  # Set specific players
            index=1,  # Start from second player
            round_complete=False  # Set round state
        )

        # Configure sequence of next players
        specific_players = [players[1], players[2], players[0]]
        queue.set_next_players(specific_players)

        # Configure round completion
        queue.set_round_complete(True)

        # Test queue state
        assert len(queue) == 3
        assert queue.get_next_player() == players[1]

        # Verify method calls
        queue.get_next_player.assert_called_once()
        queue.remove_player.assert_not_called()

    Default Behaviors:
        - get_next_player: Returns next player in rotation
        - remove_player: Removes player and adjusts index
        - reset_queue: Resets index to 0
        - is_round_complete: Checks if all players folded or all-in

    Attributes:
        players (List[MockPlayer]): List of mock players in the queue
        index (int): Current position in rotation

    All methods are MagicMocks that can be configured with custom return values
    or side effects as needed for testing.
    """

    def __init__(self, players: List[MockPlayer]):
        """Initialize the mock player queue.

        Args:
            players: List of MockPlayer objects to be included in the queue
        """
        self.players = players.copy()  # Make a copy to avoid modifying original list
        self.index = 0

        # Create mock methods that can be configured in tests
        self.get_next_player = MagicMock()
        self.remove_player = MagicMock()
        self.reset_queue = MagicMock()
        self.is_round_complete = MagicMock(return_value=False)

        # Set up default behaviors
        self.get_next_player.side_effect = self._default_get_next_player
        self.remove_player.side_effect = self._default_remove_player
        self.reset_queue.side_effect = self._default_reset_queue
        self.is_round_complete.side_effect = self._default_is_round_complete

    def _default_get_next_player(self) -> Optional[MockPlayer]:
        """Default behavior for getting next player."""
        if not self.players:
            return None
        player = self.players[self.index]
        self.index = (self.index + 1) % len(self.players)
        return player

    def _default_remove_player(self, player: MockPlayer) -> None:
        """Default behavior for removing a player."""
        if player in self.players:
            player_index = self.players.index(player)
            self.players.remove(player)
            if player_index < self.index:
                self.index -= 1
            if self.index >= len(self.players):
                self.index = 0

    def _default_reset_queue(self) -> None:
        """Default behavior for resetting the queue."""
        self.index = 0

    def _default_is_round_complete(self) -> bool:
        """Default behavior for checking if round is complete."""
        return all(player.folded or player.is_all_in for player in self.players)

    def configure_for_test(
        self,
        players: Optional[List[MockPlayer]] = None,
        index: Optional[int] = None,
        round_complete: Optional[bool] = None,
    ) -> None:
        """Configure the mock queue for testing with a single method.

        Args:
            players: Optional list of players to set
            index: Optional index to set
            round_complete: Optional boolean to set round complete status
        """
        if players is not None:
            self.players = players.copy()

        if index is not None:
            self.index = index

        if round_complete is not None:
            self.is_round_complete.return_value = round_complete

    def set_next_players(self, players: List[MockPlayer]) -> None:
        """Configure the sequence of players to be returned by get_next_player.

        Args:
            players: List of players to be returned in sequence
        """
        self.get_next_player.reset_mock()
        self.get_next_player.side_effect = players

    def set_round_complete(self, is_complete: bool) -> None:
        """Configure whether the round is complete.

        Args:
            is_complete: Boolean indicating if round is complete
        """
        self.is_round_complete.return_value = is_complete

    def __len__(self) -> int:
        """Get the number of players in the queue."""
        return len(self.players)

    def __str__(self) -> str:
        """Get a string representation of the queue state."""
        return (
            f"MockPlayerQueue: {len(self.players)} players, "
            f"current index: {self.index}"
        )
