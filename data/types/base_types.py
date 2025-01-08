from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class DeckState:
    """Represents the current state of the deck."""

    cards_remaining: int
    cards_dealt: int = 0
    cards_discarded: int = 0
    needs_shuffle: bool = False
    last_action: Optional[str] = None  # "deal", "discard", "shuffle", etc.

    def to_dict(self) -> Dict[str, Any]:
        """Convert deck state to dictionary representation."""
        return {
            "cards": {
                "remaining": self.cards_remaining,
                "dealt": self.cards_dealt,
                "discarded": self.cards_discarded,
                "total": self.cards_remaining + self.cards_dealt + self.cards_discarded,
            },
            "status": {
                "needs_shuffle": self.needs_shuffle,
                "last_action": self.last_action,
            },
        }
