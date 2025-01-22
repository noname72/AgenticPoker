from typing import List, Optional, Set
from unittest.mock import MagicMock

from tests.mocks.mock_player import MockPlayer


class MockTable:
    """Mock implementation of Table for testing.

    Provides the same interface as Table but with configurable behaviors
    and tracking capabilities for testing. Manages player rotation and betting
    action tracking.

    Attributes:
        players: List of all players in the table
        index: Current position in rotation
        needs_to_act: Players who still need to act
        acted_since_last_raise: Players who acted since last raise
        active_players: Players who haven't folded/all-in
        all_in_players: Players who are all-in
        folded_players: Players who have folded
    """

    def __init__(self, players: List[MockPlayer]):
        """Initialize the mock table with a list of players."""
        self.players = players.copy()
        self.index = 0

        # Add tracking sets to match real Table
        self.needs_to_act: Set[MockPlayer] = set(players)
        self.acted_since_last_raise: Set[MockPlayer] = set()

        # Add player state lists
        self._update_player_lists()

        # Create mock methods that can be configured in tests
        self.get_next_player = MagicMock()
        self.remove_player = MagicMock()
        self.is_round_complete = MagicMock(return_value=False)
        self.mark_player_acted = MagicMock()
        self.reset_action_tracking = MagicMock()
        self.all_players_acted = MagicMock(return_value=False)

        # Set up default behaviors
        self.get_next_player.side_effect = self._default_get_next_player
        self.remove_player.side_effect = self._default_remove_player
        self.is_round_complete.side_effect = self._default_is_round_complete
        self.mark_player_acted.side_effect = self._default_mark_player_acted
        self.reset_action_tracking.side_effect = self._default_reset_action_tracking
        self.all_players_acted.side_effect = self._default_all_players_acted

    def _update_player_lists(self) -> None:
        """Update the categorized lists of players based on their current state.

        Updates active_players, all_in_players, and folded_players lists.
        Resets the index to maintain consistent clockwise rotation.
        """
        self.active_players = [
            p for p in self.players if not p.folded and not p.is_all_in and p.chips > 0
        ]
        self.all_in_players = [p for p in self.players if p.is_all_in]
        self.folded_players = [p for p in self.players if p.folded]

        if not self.active_players:
            self.needs_to_act.clear()

        self.index = 0  # Reset index when player states change

    def _default_get_next_player(self) -> Optional[MockPlayer]:
        """Default behavior for getting next player.

        Returns the next active player in the queue, skipping folded and all-in players.
        Maintains circular rotation by wrapping around to the start when reaching the end.

        Returns:
            Optional[MockPlayer]: Next active player, or None if no active players remain
        """
        if not self.active_players:
            return None

        # Try to find next active player starting from current index
        start_index = self.index
        while True:
            # Get current player
            if self.index >= len(self.players):
                self.index = 0
            current_player = self.players[self.index]

            # Move index to next position for next call
            self.index = (self.index + 1) % len(self.players)

            # If we found an active player, return them
            if current_player in self.active_players:
                return current_player

            # If we've checked all players and found none active, return None
            if self.index == start_index:
                return None

    def _default_remove_player(self, player: MockPlayer) -> None:
        """Default behavior for removing a player."""
        if player in self.players:
            player_index = self.players.index(player)
            self.players.remove(player)
            self.needs_to_act.discard(player)  # Remove from needs_to_act
            self.acted_since_last_raise.discard(
                player
            )  # Remove from acted_since_last_raise

            # Adjust index if needed
            if player_index < self.index:
                self.index -= 1
            if self.index >= len(self.players):
                self.index = 0

            self._update_player_lists()

    def _default_is_round_complete(self) -> bool:
        """Default behavior for checking if round is complete."""
        # If all players but one have folded
        if len(self.active_players) + len(self.all_in_players) <= 1:
            return True

        # If all remaining players are all-in
        if not self.active_players and len(self.all_in_players) > 0:
            return True

        # Otherwise, continue the round
        return False

    def _default_mark_player_acted(
        self, player: MockPlayer, is_raise: bool = False
    ) -> None:
        """Default behavior for marking a player's action."""
        self.needs_to_act.discard(player)
        self.acted_since_last_raise.add(player)

        if is_raise:
            self.acted_since_last_raise = {player}
            self.needs_to_act = set(p for p in self.active_players if p != player)

    def _default_reset_action_tracking(self) -> None:
        """Default behavior for resetting action tracking."""
        self.needs_to_act = set(self.active_players)
        self.acted_since_last_raise.clear()

    def _default_all_players_acted(self) -> bool:
        """Default behavior for checking if all players have acted."""
        return self.acted_since_last_raise == set(self.active_players)

    def get_active_count(self) -> int:
        """Get the number of active players."""
        return len(self.active_players)

    def get_all_in_count(self) -> int:
        """Get the number of all-in players."""
        return len(self.all_in_players)

    def get_folded_count(self) -> int:
        """Get the number of folded players."""
        return len(self.folded_players)

    def __iter__(self):
        """Make PlayerQueue iterable through all players."""
        for player in self.players:
            yield player

    def __len__(self) -> int:
        """Get the number of players in the queue."""
        return len(self.players)

    def __getitem__(self, index: int) -> MockPlayer:
        """Get a player from the queue by index."""
        return self.players[index]

    def __contains__(self, player: MockPlayer) -> bool:
        """Check if a player is in the queue."""
        return player in self.players
