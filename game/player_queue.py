from typing import List, Optional

from game.player import Player


class PlayerQueue:
    """A circular queue to manage player turns and betting rounds in a poker game.

    This class handles player rotation, tracks betting actions, manages player states
    (active, all-in, folded), and determines when betting rounds are complete. It maintains
    the order of play and ensures proper turn progression during betting rounds.

    Attributes:
        players (List[Player]): Ordered list of all players in the game
        index (int): Current position in the player rotation (0 to len(players)-1)
        needs_to_act (Set[Player]): Players who still need to act in current betting round
        acted_since_last_raise (Set[Player]): Players who have acted since the last raise
        active_players (List[Player]): Players who haven't folded and aren't all-in
        all_in_players (List[Player]): Players who have committed all their chips
        folded_players (List[Player]): Players who have folded their hands
    """

    def __init__(self, players: List[Player]):
        """Initialize the player queue with a list of players.

        Sets up the initial player rotation and tracking sets for betting rounds.
        All players start as needing to act and no players have acted since last raise.

        Args:
            players (List[Player]): Ordered list of Player objects to be included in the queue.
                                  The order determines the seating arrangement and turn order.
        """
        self.players = players
        self.index = 0
        self.needs_to_act = set(players)  # Track players who still need to act
        self.acted_since_last_raise = (
            set()
        )  # Track players who have acted since last raise
        self._update_player_lists()

    def _update_player_lists(self) -> None:
        """Update the categorized lists of players based on their current state.

        Updates active_players, all_in_players, and folded_players lists.
        Resets the index to maintain consistent clockwise rotation.
        """
        self.active_players = [
            p for p in self.players if not p.folded and not p.is_all_in
        ]
        self.all_in_players = [p for p in self.players if p.is_all_in]
        self.folded_players = [p for p in self.players if p.folded]
        self.index = 0  # Reset index when player states change

    def get_next_player(self) -> Optional[Player]:
        """Get the next active player in the rotation who can take an action.

        Cycles through the players list starting from the current index until finding
        an active player (not folded, not all-in). Updates the index for the next call.
        Wraps around to the beginning of the list if reaching the end.

        Returns:
            Optional[Player]: The next active player who can take an action.
                            Returns None if no active players remain.
        """
        if not self.active_players:
            return None

        # Find next active player
        while True:
            if self.index >= len(self.players):
                self.index = 0
            player = self.players[self.index]
            self.index += 1
            if player in self.active_players:
                return player

    def remove_player(self, player: Player) -> None:
        """Remove a player from the queue.

        Removes player from:
        - Main players list
        - needs_to_act set
        - acted_since_last_raise set
        Then updates player lists and adjusts index if needed.

        Args:
            player (Player): The player to remove from the queue
        """
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
        if len(self.active_players) + len(self.all_in_players) <= 1:
            return True

        # If all remaining players are all-in
        if not self.active_players and len(self.all_in_players) > 0:
            return True

        # Otherwise, continue the round
        return False

    def get_active_count(self) -> int:
        """Get the number of active players (not folded, not all-in).

        Returns:
            int: Number of active players
        """
        return len(self.active_players)

    def get_all_in_count(self) -> int:
        """Get the number of all-in players.

        Returns:
            int: Number of all-in players
        """
        return len(self.all_in_players)

    def get_folded_count(self) -> int:
        """Get the number of folded players.

        Returns:
            int: Number of folded players
        """
        return len(self.folded_players)

    def mark_player_acted(self, player: Player, is_raise: bool = False) -> None:
        """Mark a player as having acted in the current betting round.

        Updates tracking sets to reflect a player's action. If the action was a raise,
        resets the acted_since_last_raise set and requires all other active players
        to act again.

        Args:
            player (Player): The player who just completed their action
            is_raise (bool): Whether the action was a raise/re-raise. Defaults to False.
                           If True, resets action tracking for other players.
        """
        self.needs_to_act.discard(player)
        self.acted_since_last_raise.add(player)

        if is_raise:
            # Reset acted_since_last_raise on a raise
            self.acted_since_last_raise = {player}
            # Everyone else needs to act again (except folded/all-in players)
            self.needs_to_act = set(p for p in self.active_players if p != player)

    def reset_action_tracking(self) -> None:
        """Reset the action tracking for a new betting round (street).

        Clears previous action history and sets all active players as needing to act.
        Should be called when moving to a new betting round (pre-flop to flop,
        flop to turn, etc.).
        """
        self.needs_to_act = set(self.active_players)
        self.acted_since_last_raise.clear()

    def all_players_acted(self) -> bool:
        """Check if all players have acted since the last raise.

        Determines if the current betting round is complete by comparing the set of
        players who have acted since the last raise with the set of active players.

        Returns:
            bool: True if all active players have acted since the last raise,
                 indicating the betting round can end.
        """
        return self.acted_since_last_raise == set(self.active_players)

    def __iter__(self):
        """Make PlayerQueue iterable through all players.

        Yields each player in the queue in order, regardless of their state
        (active, all-in, or folded).

        Yields:
            Player: Each player in the queue in sequence
        """
        for player in self.players:
            yield player

    def __len__(self) -> int:
        """Get the number of players in the queue.

        Returns:
            int: Number of players in the queue
        """
        return len(self.players)

    def __getitem__(self, index: int) -> Player:
        """Get a player from the queue by index.

        Args:
            index (int): The index of the player to retrieve

        Returns:
            Player: The player at the specified index
        """
        return self.players[index]

    def __contains__(self, player: Player) -> bool:
        """Check if a player is in the queue.

        Returns:
            bool: True if the player is in the queue, False otherwise
        """
        return player in self.players
    
        
