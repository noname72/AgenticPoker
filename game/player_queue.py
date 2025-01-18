from typing import List, Optional

from game.player import Player


class PlayerQueue:
    """A circular queue to manage player turns in a poker game.

    This class handles player rotation, removal of players, and tracks the current
    state of the playing round.

    Attributes:
        players (list): List of Player objects in the queue
        index (int): Current position in the player rotation
    """

    def __init__(self, players: List[Player]):
        """Initialize the player queue.

        Args:
            players (list): List of Player objects to be included in the queue
        """
        self.players = players
        self.index = 0

    def get_next_player(self) -> Optional[Player]:
        """Get the next player in the rotation.

        Returns:
            Player: The next player in the queue, or None if queue is empty.
            The same player will not be returned again until all other players
            have had their turns.
        """
        if not self.players:
            return None
        player = self.players[self.index]
        self.index = (self.index + 1) % len(self.players)
        return player

    def remove_player(self, player: Player) -> None:
        """Remove a player from the queue.

        Args:
            player (Player): The player to remove from the queue

        Note:
            If the removed player was at or before the current index,
            the index will be adjusted to maintain the correct rotation.
        """
        if player in self.players:
            player_index = self.players.index(player)
            self.players.remove(player)
            if player_index < self.index:
                self.index -= 1
            if self.index >= len(self.players):
                self.index = 0

    def reset_queue(self) -> None:
        """Reset the queue to start from the beginning.

        This resets the index to 0, making the next get_next_player() call
        return the first player in the queue.
        """
        self.index = 0

    def is_round_complete(self) -> bool:
        """Check if the current round of play is complete.

        A round is complete if:
        - All players have folded except one, or
        - All remaining players are all-in, or
        - All active players have acted and bets are equal

        Returns:
            bool: True if the round is complete, False otherwise.
        """
        # If all players but one have folded
        active_players = [p for p in self.players if not p.folded]
        if len(active_players) <= 1:
            return True

        # If all remaining players are all-in
        if all(p.is_all_in or p.folded for p in self.players):
            return True

        # Otherwise, continue the round
        return False
