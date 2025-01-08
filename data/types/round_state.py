from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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

    @classmethod
    def new_round(cls, round_number: int) -> "RoundState":
        """Create a new round state for the start of a hand."""
        return cls(
            phase=RoundPhase.PREFLOP,
            current_bet=0,
            round_number=round_number,
            raise_count=0,
        )
