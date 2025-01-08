from enum import Enum
from typing import Optional

from pydantic import BaseModel


class PlayerPosition(str, Enum):
    """Represents standard poker table positions."""

    DEALER = "dealer"
    SMALL_BLIND = "small_blind"
    BIG_BLIND = "big_blind"
    UNDER_THE_GUN = "under_the_gun"
    MIDDLE = "middle"
    CUTOFF = "cutoff"
    OTHER = "other"


class PlayerState(BaseModel):
    """Represents the state of a player in the game."""

    # Basic player info
    name: str
    chips: int
    bet: int = 0
    folded: bool = False

    # Position and role
    position: PlayerPosition
    seat_number: Optional[int] = None
    is_dealer: bool = False
    is_small_blind: bool = False
    is_big_blind: bool = False

    # Hand information
    hand: Optional[str] = None
    hand_rank: Optional[str] = None

    # Betting round state
    has_acted: bool = False
    total_bet_this_round: int = 0
    last_action: Optional[str] = None
    last_raise_amount: Optional[int] = None

    # Game status
    is_all_in: bool = False
    is_active: bool = True
    chips_at_start_of_hand: Optional[int] = None

    # Historical tracking
    hands_played: int = 0
    hands_won: int = 0
    total_winnings: int = 0
    biggest_pot_won: int = 0
