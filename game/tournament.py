import logging
from datetime import datetime, timedelta
from typing import Dict, List

from .game import AgenticPoker


class PokerTournament:
    """
    Manages a multi-table tournament structure using one or more AgenticPoker instances.

    Handles:
        - Multiple levels with increasing blinds and antes
        - Player elimination across tables
        - Scheduling and time-based logic for blind increases
        - Final table creation when enough players are eliminated
        - (Optional) Rebuys, seat reassignments, etc.
    """

    def __init__(
        self,
        players: List,
        buy_in: int,
        starting_chips: int,
        blind_schedule: List[Dict],
        level_duration_minutes: int = 15,
        # ... other tournament parameters as desired ...
    ):
        """
        Initialize the tournament.

        Args:
            players (List): List of player objects or names.
            buy_in (int): The buy-in cost (optional, for tracking).
            starting_chips (int): Number of chips each player starts with.
            blind_schedule (List[Dict]): Sequence of blind/ante structures,
                e.g. [{'small_blind': 50, 'big_blind': 100, 'ante': 10}, ...]
            level_duration_minutes (int): How long each blind level lasts.
        """
        self.logger = logging.getLogger(__name__)
        self.players = players
        self.buy_in = buy_in
        self.starting_chips = starting_chips
        self.blind_schedule = blind_schedule
        self.level_duration = timedelta(minutes=level_duration_minutes)
        self.current_level_index = 0
        self.tournament_start_time = datetime.now()
        self.tables: List[AgenticPoker] = []
        self._init_tables()

    def _init_tables(self) -> None:
        """
        Create one or more AgenticPoker instances (tables) depending on
        how many players you have, seating them accordingly.
        This example starts as a single table with all players.
        """
        blind_info = self.blind_schedule[self.current_level_index]
        # For simplicity, put all players at one table:
        table = AgenticPoker(
            players=self.players,
            starting_chips=self.starting_chips,
            small_blind=blind_info["small_blind"],
            big_blind=blind_info["big_blind"],
            ante=blind_info.get("ante", 0),
        )
        self.tables.append(table)

    def _update_structure(self) -> None:
        """
        Transition to the next blind level if enough time has passed.
        This method can be called periodically or after each hand/round.
        """
        elapsed = datetime.now() - self.tournament_start_time
        levels_passed = int(elapsed // self.level_duration)
        if levels_passed > self.current_level_index and levels_passed < len(
            self.blind_schedule
        ):
            self.current_level_index = levels_passed
            new_blind_info = self.blind_schedule[self.current_level_index]
            self.logger.info(
                f"=== ADVANCING TO LEVEL {self.current_level_index + 1} ===\n"
                f"Blinds: {new_blind_info['small_blind']}/{new_blind_info['big_blind']}, "
                f"Ante: {new_blind_info.get('ante', 0)}"
            )
            # Update each active table's blinds/antes for subsequent rounds
            for table in self.tables:
                table.small_blind = new_blind_info["small_blind"]
                table.big_blind = new_blind_info["big_blind"]
                table.ante = new_blind_info.get("ante", 0)

    def start_tournament(self) -> None:
        """
        Main loop for running the tournament. In a real system, you'd handle
        multi-table concurrency, user input, rebuys, etc.
        """
        self.logger.info("Starting the tournament!")

        while not self._tournament_ended():
            self._update_structure()

            # In a single-table scenario, just start the game or continue it:
            for table in self.tables:
                table.start_game()

            # (Optional) If you had multiple tables:
            # - Check elimination, seat guests, merge tables, etc.

        self.logger.info("Tournament has ended! Determining final results...")
        self._finalize_results()

    def _tournament_ended(self) -> bool:
        """
        Check if the tournament is over: e.g., only one player remains,
        or however else you want to define "end condition."
        """
        active_players = []
        for table in self.tables:
            active_players.extend(table.players)
        # If <= 1 player remains OR all but one are bankrupt, tournament is done:
        return len([p for p in active_players if p.chips > 0]) <= 1

    def _finalize_results(self) -> None:
        """
        Collate final standings, handle payouts, etc.
        """
        # Example simplistic approach:
        final_player = None
        for table in self.tables:
            for p in table.players:
                if p.chips > 0:
                    final_player = p
                    break
        if final_player:
            self.logger.info(
                f"{final_player.name} is the champion with {final_player.chips} chips!"
            )
        else:
            self.logger.info("No winner could be determined (unusual situation).")


# ... you could add advanced features like rebuys, multi-table merging,
# payouts, or final table logic
