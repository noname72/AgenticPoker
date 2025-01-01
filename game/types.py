from typing import List, NamedTuple, TypedDict
from .player import Player
from dataclasses import dataclass, field


@dataclass
class SidePot:
    """Represents a side pot in poker with its amount and eligible players."""

    amount: int = field(default=0)
    eligible_players: List[Player] = field(default_factory=list)


class SidePotView(TypedDict):
    """View-model for displaying side pot information"""

    amount: int
    eligible_players: List[str]
