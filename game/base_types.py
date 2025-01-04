from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


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


@dataclass
class PlayerState:
    """Represents the complete state of a player in the game."""

    # Basic player info
    name: str
    chips: int
    bet: int
    folded: bool

    # Position and role
    position: PlayerPosition  # Enum for standard positions
    seat_number: Optional[int] = None  # Physical seat at table (0-based)
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert player state to dictionary representation."""
        return {
            "basic_info": {
                "name": self.name,
                "chips": self.chips,
                "bet": self.bet,
                "folded": self.folded,
            },
            "position": {
                "type": self.position.value,
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


@dataclass
class RoundState:
    """Represents the state of a single round of poker.

    Tracks all information specific to the current round including
    betting phases, player actions, and pot evolution.
    """

    # Round identification
    round_number: int
    phase: str  # "pre_draw" or "post_draw"

    # Betting round state
    current_bet: int = 0
    raise_count: int = 0
    last_raiser: Optional[str] = None  # Name of player who last raised
    last_aggressor: Optional[str] = None  # Name of last player to bet/raise
    needs_to_act: List[str] = field(
        default_factory=list
    )  # Names of players who still need to act
    acted_this_phase: List[str] = field(
        default_factory=list
    )  # Names of players who have acted

    # Pot tracking
    main_pot: int = 0
    side_pots: List[Dict[str, Any]] = field(default_factory=list)

    # Draw phase tracking
    cards_drawn: Dict[str, int] = field(
        default_factory=dict
    )  # Player name -> number of cards drawn

    # Round completion
    is_complete: bool = False
    winner: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert round state to dictionary representation."""
        return {
            "round": {
                "number": self.round_number,
                "phase": self.phase,
                "is_complete": self.is_complete,
                "winner": self.winner,
            },
            "betting": {
                "current_bet": self.current_bet,
                "raise_count": self.raise_count,
                "last_raiser": self.last_raiser,
                "last_aggressor": self.last_aggressor,
                "needs_to_act": self.needs_to_act,
                "acted_this_phase": self.acted_this_phase,
            },
            "pot": {"main": self.main_pot, "side_pots": self.side_pots},
            "draw_phase": {"cards_drawn": self.cards_drawn},
        }

    @classmethod
    def new_round(cls, round_number: int) -> "RoundState":
        """Create a new round state."""
        return cls(round_number=round_number, phase="pre_draw")

    def advance_phase(self) -> None:
        """Advance to the next phase of the round."""
        if self.phase == "pre_draw":
            self.phase = "post_draw"
            self.current_bet = 0
            self.raise_count = 0
            self.last_raiser = None
            self.last_aggressor = None
            self.needs_to_act.clear()
            self.acted_this_phase.clear()
        else:
            self.is_complete = True

    def record_action(
        self, player_name: str, action: str, amount: Optional[int] = None
    ) -> None:
        """Record a player's action in the current phase."""
        self.acted_this_phase.append(player_name)
        if player_name in self.needs_to_act:
            self.needs_to_act.remove(player_name)

        if action in ["bet", "raise"]:
            self.last_raiser = player_name
            self.last_aggressor = player_name
            self.raise_count += 1
            if amount is not None:
                self.current_bet = amount
