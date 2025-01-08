from typing import List

from pydantic import BaseModel


class SidePot(BaseModel):
    """Represents a side pot in poker when players are all-in."""

    amount: int
    eligible_players: List[str]


class PotState(BaseModel):
    """Represents the state of all pots in the game."""

    main_pot: int = 0
    side_pots: List[SidePot] = []
    total_pot: int = 0

    def add_to_main_pot(self, amount: int) -> None:
        """Add chips to the main pot."""
        self.main_pot += amount
        self.total_pot += amount

    def add_side_pot(self, amount: int, players: List[str]) -> None:
        """Create a new side pot."""
        self.side_pots.append(SidePot(amount=amount, eligible_players=players))
        self.total_pot += amount
