from typing import List, NamedTuple, TypedDict
from .player import Player


class SidePot(NamedTuple):
    """Represents a side pot with its amount and eligible players"""

    amount: int
    eligible_players: List[Player]


class SidePotView(TypedDict):
    """View-model for displaying side pot information"""

    amount: int
    eligible_players: List[str]
