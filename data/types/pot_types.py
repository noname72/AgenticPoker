from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from game.player import Player


@dataclass
class SidePot:
    """Represents a side pot in poker with its amount and eligible players."""

    amount: int = field(default=0)
    eligible_players: List[Player] = field(default_factory=list)


@dataclass
class SidePotView:
    """View-model for displaying side pot information."""

    amount: int
    eligible_players: List[str]


@dataclass
class PotState:
    """Represents the current state of all pots in the game."""

    main_pot: int = 0
    side_pots: List[Dict[str, Any]] = field(default_factory=list)
    total_chips_in_play: int = 0  # Total chips across all pots and player bets

    def to_dict(self) -> Dict[str, Any]:
        """Convert pot state to dictionary representation."""
        return {
            "main_pot": self.main_pot,
            "side_pots": [
                {"amount": pot["amount"], "eligible_players": pot["eligible_players"]}
                for pot in self.side_pots
            ],
            "total_chips_in_play": self.total_chips_in_play,
        }
