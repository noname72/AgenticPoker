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
