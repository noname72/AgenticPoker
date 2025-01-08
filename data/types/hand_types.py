from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HandState:
    """Represents the state of a poker hand."""

    cards: List[str]  # String representations of cards (e.g., "A♠")
    rank: Optional[str] = None  # Description of hand rank if evaluated
    rank_value: Optional[int] = None  # Numerical rank value
    tiebreakers: List[int] = field(default_factory=list)
    is_evaluated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert hand state to dictionary representation."""
        return {
            "cards": self.cards,
            "evaluation": {
                "rank": self.rank,
                "rank_value": self.rank_value,
                "tiebreakers": self.tiebreakers,
                "is_evaluated": self.is_evaluated,
            },
        }
