from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class PlayerPosition(str, Enum):
    """Represents possible player positions at the table."""

    DEALER = "dealer"
    SMALL_BLIND = "small_blind"
    BIG_BLIND = "big_blind"
    UNDER_THE_GUN = "under_the_gun"
    MIDDLE = "middle"
    CUTOFF = "cutoff"
    OTHER = "other"


@dataclass
class PlayerState:
    """Represents the complete state of a player in the game."""

    # Basic player info
    name: str
    chips: int
    bet: int = 0
    folded: bool = False

    # Position and role
    position: Optional[PlayerPosition] = None
    seat_number: Optional[int] = None
    is_dealer: bool = False
    is_small_blind: bool = False
    is_big_blind: bool = False

    # Hand information
    hand: Optional[str] = None  # String representation of hand if known
    hand_rank: Optional[str] = None  # Description of hand rank if evaluated

    # Betting round state
    has_acted: bool = False  # Whether player has acted in current round
    total_bet_this_round: int = 0  # Total amount bet in current round
    last_action: Optional[str] = None  # Last action taken (fold/call/raise)
    last_raise_amount: Optional[int] = None  # Amount of last raise if any

    # Game status
    is_all_in: bool = False
    is_active: bool = True  # False if folded or all-in
    chips_at_start_of_hand: Optional[int] = None

    # Historical tracking
    hands_played: int = 0
    hands_won: int = 0
    total_winnings: int = 0
    biggest_pot_won: int = 0

    def to_dict(self) -> dict:
        """Convert player state to dictionary format."""
        return {
            "basic_info": {
                "name": self.name,
                "chips": self.chips,
                "bet": self.bet,
                "folded": self.folded,
            },
            "position": {
                "type": str(self.position.value) if self.position else None,
                "seat": self.seat_number,
                "is_dealer": self.is_dealer,
                "is_small_blind": self.is_small_blind,
                "is_big_blind": self.is_big_blind,
            },
            "hand": {"cards": self.hand, "rank": self.hand_rank},
            "betting": {
                "has_acted": self.has_acted,
                "total_bet": self.total_bet_this_round,
                "last_action": self.last_action,
                "last_raise": self.last_raise_amount,
            },
            "status": {
                "all_in": self.is_all_in,
                "active": self.is_active,
                "chips_at_start": self.chips_at_start_of_hand,
            },
            "history": {
                "hands_played": self.hands_played,
                "hands_won": self.hands_won,
                "total_winnings": self.total_winnings,
                "biggest_pot": self.biggest_pot_won,
            },
        }
