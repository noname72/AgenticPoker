from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, validator


class RoundPhase(str, Enum):
    """Represents the different phases of a poker round."""

    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"
    PRE_DRAW = "pre_draw"
    POST_DRAW = "post_draw"


class RoundState(BaseModel):
    """Represents the state of a betting round."""

    phase: RoundPhase
    current_bet: int
    round_number: int
    raise_count: int = 0
    dealer_position: Optional[int] = None
    small_blind_position: Optional[int] = None
    big_blind_position: Optional[int] = None
    first_bettor_index: Optional[int] = None
    main_pot: int = 0
    side_pots: List[Dict[str, Any]] = []

    # Add fields for tracking betting actions
    last_raiser: Optional[str] = None
    last_aggressor: Optional[str] = None
    needs_to_act: List[str] = []
    acted_this_phase: List[str] = []
    is_complete: bool = False
    winner: Optional[str] = None

    @validator("current_bet", "round_number", "raise_count", "main_pot")
    def validate_non_negative(cls, v):
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return v

    @classmethod
    def new_round(cls, round_number: int, game_type: str) -> "RoundState":
        """Create a new round state for the start of a hand."""
        if game_type == "texas-holdem":
            return cls(
                phase=RoundPhase.PREFLOP,
                current_bet=0,
                round_number=round_number,
                raise_count=0,
            )
        elif game_type == "5-card-draw":
            return cls(
                phase=RoundPhase.PRE_DRAW,
                current_bet=0,
                round_number=round_number,
                raise_count=0,
            )
        else:
            raise ValueError(f"Unsupported game type: {game_type}")
