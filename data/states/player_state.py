from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import BaseModel, Field

from data.types.player_types import PlayerPosition

if TYPE_CHECKING:
    from game import Player


class PlayerState(BaseModel):
    """Represents the complete state of a player in a poker game.

    This Pydantic model maintains all relevant information about a player during a poker game,
    including their current chips, betting status, position, hand information, and historical
    statistics. It provides serialization/deserialization and validation of player data.

    Attributes:
        Basic Info:
            name (str): Player's display name
            chips (int): Current chip count (must be >= 0)
            bet (int): Current bet amount in the pot (must be >= 0)
            folded (bool): Whether the player has folded this hand

        Position and Role:
            position (PlayerPosition): Player's position at the table (enum)
            seat_number (Optional[int]): Physical seat number (0-based)
            is_dealer (bool): Whether player has the dealer button
            is_small_blind (bool): Whether player is in small blind position
            is_big_blind (bool): Whether player is in big blind position

        Hand Information:
            hand (Optional[str]): String representation of player's cards
            hand_rank (Optional[str]): Description of hand strength if evaluated

        Betting Round State:
            has_acted (bool): Whether player has acted in current betting round
            total_bet_this_round (int): Amount bet in current betting round
            last_action (Optional[str]): Last action taken (fold/call/raise)
            last_raise_amount (Optional[int]): Size of player's last raise

        Game Status:
            is_all_in (bool): Whether player is all-in
            is_active (bool): Whether player is still in hand
            chips_at_start_of_hand (Optional[int]): Chip count when hand began

        Historical Stats:
            hands_played (int): Total number of hands played
            hands_won (int): Total number of hands won
            total_winnings (int): Cumulative winnings
            biggest_pot_won (int): Largest pot won in a single hand

    Methods:
        from_player: Create a PlayerState instance from a Player object
        to_dict: Convert player state to a nested dictionary representation
        get: Dictionary-style attribute access with default value support
    """

    # Basic player info
    name: str
    chips: int = Field(ge=0)
    bet: int = Field(ge=0)
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
    total_bet_this_round: int = Field(
        default=0, ge=0
    )  # Total amount bet in current round
    last_action: Optional[str] = None  # Last action taken (fold/call/raise)
    last_raise_amount: Optional[int] = None  # Amount of last raise if any

    # Game status
    is_all_in: bool = False
    is_active: bool = True  # False if folded or all-in
    chips_at_start_of_hand: Optional[int] = None

    # Historical tracking
    hands_played: int = Field(default=0, ge=0)
    hands_won: int = Field(default=0, ge=0)
    total_winnings: int = Field(default=0, ge=0)
    biggest_pot_won: int = Field(default=0, ge=0)

    def __getitem__(self, key: str) -> Any:
        """Enable dictionary-style access to player state attributes."""
        if hasattr(self, key):
            return getattr(self, key)
        return self.dict()[key]

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for checking if attributes exist."""
        if hasattr(self, key):
            return True
        return key in self.dict()

    def get(self, key: str, default: Any = None) -> Any:
        """Implement dict-style .get() method."""
        try:
            return self[key]
        except (KeyError, AttributeError):
            return default

    def to_dict(self) -> Dict[str, Any]:
        """Convert player state to dictionary representation."""
        base_dict = self.dict()

        return {
            "basic_info": {
                "name": self.name,
                "chips": self.chips,
                "bet": self.bet,
                "folded": self.folded,
            },
            "position": {
                "type": str(self.position.value),
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
            # Add flattened access to common attributes
            **base_dict,
            "position": str(self.position.value),
            "hand": str(self.hand) if self.hand else None,
            "hand_rank": str(self.hand_rank) if self.hand_rank else None,
        }

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_player(cls, player: "Player") -> "PlayerState":
        """Create a PlayerState instance from a Player object.

        Args:
            player: The player instance to create state from

        Returns:
            PlayerState: A new PlayerState instance representing the player's current state
        """
        return cls(
            name=player.name,
            chips=player.chips,
            bet=player.bet,
            folded=player.folded,
            position=getattr(player, "position", PlayerPosition.OTHER),
            seat_number=getattr(player, "seat_number", None),
            is_dealer=getattr(player, "is_dealer", False),
            is_small_blind=getattr(player, "is_small_blind", False),
            is_big_blind=getattr(player, "is_big_blind", False),
            hand=str(player.hand) if hasattr(player, "hand") else None,
            hand_rank=getattr(player, "hand_rank", None),
            has_acted=getattr(player, "has_acted", False),
            total_bet_this_round=getattr(player, "total_bet_this_round", 0),
            last_action=getattr(player, "last_action", None),
            last_raise_amount=getattr(player, "last_raise_amount", None),
            is_all_in=getattr(player, "is_all_in", False),
            is_active=not player.folded and player.chips > 0,
            chips_at_start_of_hand=getattr(player, "chips_at_start_of_hand", None),
            hands_played=getattr(player, "hands_played", 0),
            hands_won=getattr(player, "hands_won", 0),
            total_winnings=getattr(player, "total_winnings", 0),
            biggest_pot_won=getattr(player, "biggest_pot_won", 0),
        )
