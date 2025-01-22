"""
This module provides the Table class which manages a poker table and its players.

The Table class handles:
- Player seating and rotation
- Betting round management
- Player state tracking (active, all-in, folded)
- Turn progression during betting rounds

Key concepts:
- Active players: Players who can still act (have chips, haven't folded/all-in)
- Betting rounds: A sequence of player actions that continues until all active 
  players have either called the current bet or folded
- Action tracking: Monitoring which players need to act and who has acted since 
  the last raise

Example usage:
    # Create players
    players = [
        Player("Alice", 1000),
        Player("Bob", 1000),
        Player("Charlie", 1000)
    ]

    # Initialize the table
    table = Table(players)

    # Start a new betting round
    table.reset_action_tracking()

    # Process betting round
    while not table.is_round_complete():
        current_player = table.get_next_player()
        if current_player is None:
            break

        # Handle player actions
        # ... player makes decision ...
        table.mark_player_acted(current_player, is_raise=action_was_raise)

    # Query table state
    active_players = table.active_players()
    all_in_players = table.all_in_players()
    folded_players = table.folded_players()
"""

from typing import List, Optional

from game.player import Player
from loggers.table_logger import TableLogger


class Table:
    """A poker table that manages players and coordinates gameplay.

    The Table represents a poker table where players are seated and betting rounds occur.
    It manages the flow of the game by tracking player states, coordinating betting rounds,
    and ensuring proper turn order.

    Core responsibilities:
    - Maintains player seating and rotation order
    - Tracks player states (active, all-in, folded)
    - Manages betting rounds and player actions
    - Determines when betting rounds are complete
    - Provides player state queries (active, inactive, all-in, folded)

    Betting rounds proceed until either:
    1. Only one active player remains
    2. All active players have acted since the last raise

    Attributes:
        players (List[Player]): Ordered list of players at the table, representing seating order
        index (int): Current dealer position in the rotation (0 to len(players)-1)
        needs_to_act (Set[Player]): Set of players who still need to act in current round
        acted_since_last_raise (Set[Player]): Set of players who have acted since last raise
    """

    def __init__(self, players: List[Player]):
        """Initialize the table with a list of players.

        Sets up the initial player rotation and tracking sets for betting rounds.
        All players start as needing to act and no players have acted since last raise.

        Args:
            players (List[Player]): Ordered list of Player objects to be included in the table.
                                  The order determines the seating arrangement and turn order.
        """
        self.players = players
        self.index = 0
        self.needs_to_act = set(players)  # Track players who still need to act
        self.acted_since_last_raise = (
            set()
        )  # Track players who have acted since last raise
        TableLogger.log_table_creation(len(players))

    def get_next_player(self) -> Optional[Player]:
        """Get the next active player in the rotation who can take an action.

        Cycles through the players list starting from the current index until finding
        an active player (not folded, not all-in). Updates the index for the next call.
        Wraps around to the beginning of the list if reaching the end.

        Returns:
            Optional[Player]: The next active player who can take an action.
                            Returns None if no active players remain.
        """
        if not self.active_players():
            return None

        # Find next active player
        while True:
            if self.index >= len(self.players):
                self.index = 0
            player = self.players[self.index]
            self.index += 1
            if player in self.active_players():
                TableLogger.log_next_player(
                    player.name, self.index - 1, [p.name for p in self.needs_to_act]
                )
                return player

    def is_round_complete(self) -> bool:
        """Determine if the current betting round is complete.

        A betting round is considered complete when either:
        1. Only one active player remains (others have folded or are all-in), or
        2. All active players have acted since the last raise (everyone has had a chance
           to call/fold/raise the current bet)

        The method logs debugging information about:
        - The completion status
        - Which players have acted since the last raise
        - Current active players

        Returns:
            bool: True if the betting round is complete, False otherwise
        """
        # Round is complete if only 1 active player or if all active players have acted since last raise
        complete = len(self.acted_since_last_raise) == len(self.active_players())

        if complete:
            reason = (
                "only one active player"
                if len(self.active_players()) == 1
                else "all active players have acted"
            )
            TableLogger.log_round_complete(reason)

        TableLogger.log_debug(
            f"Acted since last raise: {[p.name for p in self.acted_since_last_raise]}"
        )
        TableLogger.log_debug(
            f"Active players: {[p.name for p in self.active_players()]}"
        )
        return complete

    def get_active_count(self) -> int:
        """Get the number of active players (not folded, not all-in).

        Returns:
            int: Number of active players
        """
        return len(self.active_players())

    def get_all_in_count(self) -> int:
        """Get the number of all-in players.

        Returns:
            int: Number of all-in players
        """
        return len(self.all_in_players())

    def get_folded_count(self) -> int:
        """Get the number of folded players.

        Returns:
            int: Number of folded players
        """
        return len(self.folded_players())

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

        TableLogger.log_player_acted(
            player.name,
            is_raise,
            [p.name for p in self.needs_to_act],
            [p.name for p in self.acted_since_last_raise],
        )

        if is_raise:
            # Reset acted_since_last_raise on a raise
            self.acted_since_last_raise = {player}
            # Everyone else needs to act again (except folded/all-in players)
            self.needs_to_act = set(p for p in self.active_players() if p != player)

    def reset_action_tracking(self) -> None:
        """Reset the action tracking for a new betting round (street).

        Clears previous action history and sets all active players as needing to act.
        Should be called when moving to a new betting round (pre-flop to flop,
        flop to turn, etc.).
        """
        # Only add active players to needs_to_act
        self.needs_to_act = set(self.active_players())
        self.acted_since_last_raise.clear()
        self.index = 0

        TableLogger.log_action_tracking_reset([p.name for p in self.active_players()])

    def all_players_acted(self) -> bool:
        """Check if all active players have acted since the last raise.

        This method is used to determine if the current betting sequence can be completed.
        It compares the number of players who have acted since the last raise against
        the number of active players who can still make decisions.

        The method logs the result and player counts for debugging purposes.

        Returns:
            bool: True if all active players have acted since the last raise,
                  False if there are still players who need to act

        Note:
            This differs from is_round_complete() in that it only checks the action condition,
            not whether there's only one active player remaining.
        """
        acted = len(self.acted_since_last_raise) == len(self.active_players())
        TableLogger.log_debug(f"All players acted: {acted}")
        return acted

    def active_players(self) -> List[Player]:
        """Get the list of active players who can take actions.

        Active players are those who:
        - Have not folded
        - Are not all-in
        - Have chips remaining

        Returns:
            List[Player]: List of players who can still act in the current hand
        """
        active = [
            p for p in self.players if not p.folded and not p.is_all_in and p.chips > 0
        ]
        TableLogger.log_table_state(
            len(active), len(self.all_in_players()), len(self.folded_players())
        )
        return active

    def inactive_players(self) -> List[Player]:
        """Get the list of players who cannot take actions.

        Inactive players are those who:
        - Have folded
        - Are all-in
        - Have no chips remaining

        Returns:
            List[Player]: List of players who cannot act in the current hand
        """
        return [p for p in self.players if p.folded or p.is_all_in or p.chips == 0]

    def all_in_players(self) -> List[Player]:
        """Get the list of players who are all-in.

        Returns:
            List[Player]: List of players who have committed all their chips
        """
        return [p for p in self.players if p.is_all_in]

    def folded_players(self) -> List[Player]:
        """Get the list of players who have folded.

        Returns:
            List[Player]: List of players who have folded their hands
        """
        return [p for p in self.players if p.folded]

    def __iter__(self):
        """Make Table iterable through all players.

        Yields each player in the table in order, regardless of their state
        (active, all-in, or folded).

        Yields:
            Player: Each player in the table in sequence
        """
        for player in self.players:
            yield player

    def __len__(self) -> int:
        """Get the number of players in the table.

        Returns:
            int: Number of players in the table
        """
        return len(self.players)

    def __getitem__(self, index: int) -> Player:
        """Get a player from the table by index.

        Args:
            index (int): The index of the player to retrieve

        Returns:
            Player: The player at the specified index
        """
        return self.players[index]

    def __contains__(self, player: Player) -> bool:
        """Check if a player is in the table.

        Returns:
            bool: True if the player is in the table, False otherwise
        """
        return player in self.players
