from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict

from .base_types import DeckState, PlayerState, PotState, RoundState
from .player import Player


@dataclass
class GameState:
    """Represents the complete state of a poker game."""

    # Required fields (no defaults)
    players: List[PlayerState]
    dealer_position: int
    small_blind: int
    big_blind: int
    ante: int
    min_bet: int
    round_state: RoundState
    pot_state: PotState
    deck_state: DeckState

    # Optional fields (with defaults)
    active_player_position: Optional[int] = None
    max_raise_multiplier: int = 3
    max_raises_per_round: int = 4

    def copy(self) -> "GameState":
        """Create a deep copy of the game state."""
        return deepcopy(self)

    def to_dict(self) -> Dict[str, Any]:
        """Convert game state to dictionary representation."""
        return {
            "config": {
                "small_blind": self.small_blind,
                "big_blind": self.big_blind,
                "ante": self.ante,
                "min_bet": self.min_bet,
                "max_raise_multiplier": self.max_raise_multiplier,
                "max_raises_per_round": self.max_raises_per_round,
            },
            "players": [p.to_dict() for p in self.players],
            "positions": {
                "dealer": self.dealer_position,
                "active_player": self.active_player_position,
            },
            "round_state": self.round_state.to_dict(),
            "pot_state": self.pot_state.to_dict(),
            "deck_state": self.deck_state.to_dict(),
            # Add pot directly at top level for backward compatibility
            "pot": self.pot_state.main_pot,
            "current_bet": (
                self.round_state.current_bet
                if hasattr(self.round_state, "current_bet")
                else 0
            ),
        }

    def __getitem__(self, key: str) -> Any:
        """Enable dictionary-style access to game state attributes."""
        if hasattr(self, key):
            return getattr(self, key)
        # Convert to dict for legacy dictionary access
        return self.to_dict()[key]

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for checking if attributes exist."""
        if hasattr(self, key):
            return True
        return key in self.to_dict()


@dataclass
class SidePot:
    """Represents a side pot in poker with its amount and eligible players."""

    amount: int = field(default=0)
    eligible_players: List[Player] = field(default_factory=list)


class SidePotView(TypedDict):
    """View-model for displaying side pot information"""

    amount: int
    eligible_players: List[str]
