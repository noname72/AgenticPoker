from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, validator


class RoundPhase(str, Enum):
    """Represents the different phases of a poker round."""

    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"
    PRE_DRAW = "pre_draw"
    POST_DRAW = "post_draw"


@dataclass
class RoundState:
    """Represents the state of a poker round."""

    phase: RoundPhase
    current_bet: int
    round_number: int
    raise_count: int = 0
    dealer_position: Optional[int] = None
    small_blind_position: Optional[int] = None
    big_blind_position: Optional[int] = None
    first_bettor_index: Optional[int] = None
    main_pot: int = 0
    side_pots: List[Dict[str, Any]] = field(default_factory=list)

    # Add fields for tracking betting actions
    last_raiser: Optional[str] = None
    last_aggressor: Optional[str] = None
    needs_to_act: List[str] = field(default_factory=list)
    acted_this_phase: Set[str] = field(default_factory=set)
    is_complete: bool = False
    winner: Optional[str] = None

    def __post_init__(self):
        """Validate the state after initialization."""
        self.validate_non_negative()

    def validate_non_negative(self) -> None:
        """Validate that numeric fields are non-negative."""
        for field_name in ["current_bet", "round_number", "raise_count", "main_pot"]:
            value = getattr(self, field_name)
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative")

    @classmethod
    def new_round(cls, round_number: int) -> "RoundState":
        """Create a new round state for the start of a hand."""
        return cls(
            phase=RoundPhase.PRE_DRAW,
            current_bet=0,
            round_number=round_number,
            raise_count=0,
        )

    def to_dict(self) -> Dict:
        """Convert round state to a dictionary."""
        return {
            "phase": self.phase.value,  # Convert enum to string
            "current_bet": self.current_bet,
            "round_number": self.round_number,
            "raise_count": self.raise_count,
            "dealer_position": self.dealer_position,
            "small_blind_position": self.small_blind_position,
            "big_blind_position": self.big_blind_position,
            "first_bettor_index": self.first_bettor_index,
            "main_pot": self.main_pot,
            "side_pots": self.side_pots,
            "last_raiser": self.last_raiser,
            "last_aggressor": self.last_aggressor,
            "needs_to_act": list(
                self.needs_to_act
            ),  # Convert to list for JSON serialization
            "acted_this_phase": list(self.acted_this_phase),  # Convert set to list
            "is_complete": self.is_complete,
            "winner": self.winner,
        }
