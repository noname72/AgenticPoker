from dataclasses import dataclass
from typing import Any, Dict, Optional

from data.types.base_types import PlayerPosition


@dataclass
class PlayerState:
    """Represents the complete state of a player in the game.

    This class maintains all relevant information about a player during a poker game,
    including their current chips, betting status, position, hand information, and
    historical statistics.

    Attributes:
        name (str): Player's display name
        chips (int): Current chip count
        bet (int): Current bet amount in the pot
        folded (bool): Whether the player has folded this hand
        position (PlayerPosition): Player's position at the table
        seat_number (Optional[int]): Physical seat number (0-based)
        is_dealer (bool): Whether player has the dealer button
        is_small_blind (bool): Whether player is in small blind position
        is_big_blind (bool): Whether player is in big blind position
        hand (Optional[str]): String representation of player's cards
        hand_rank (Optional[str]): Description of hand strength if evaluated
        has_acted (bool): Whether player has acted in current betting round
        total_bet_this_round (int): Amount bet in current betting round
        last_action (Optional[str]): Last action taken (fold/call/raise)
        last_raise_amount (Optional[int]): Size of player's last raise
        is_all_in (bool): Whether player is all-in
        is_active (bool): Whether player is still in hand
        chips_at_start_of_hand (Optional[int]): Chip count when hand began
        hands_played (int): Total number of hands played
        hands_won (int): Total number of hands won
        total_winnings (int): Cumulative winnings
        biggest_pot_won (int): Largest pot won in a single hand
    """

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

    def __getitem__(self, key: str) -> Any:
        """Enable dictionary-style access to player state attributes.

        Args:
            key (str): The attribute name to access

        Returns:
            Any: The value of the requested attribute

        Raises:
            KeyError: If the attribute doesn't exist
        """
        if hasattr(self, key):
            return getattr(self, key)
        # Convert to dict for legacy dictionary access
        return self.to_dict()[key]

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for checking if attributes exist.

        Args:
            key (str): The attribute name to check

        Returns:
            bool: True if the attribute exists, False otherwise
        """
        if hasattr(self, key):
            return True
        return key in self.to_dict()

    def get(self, key: str, default: Any = None) -> Any:
        """Implement dict-style .get() method.

        Args:
            key (str): The attribute name to access
            default (Any, optional): Value to return if key doesn't exist. Defaults to None.

        Returns:
            Any: The value of the requested attribute or the default value
        """
        try:
            return self[key]
        except (KeyError, AttributeError):
            return default

    def to_dict(self) -> Dict[str, Any]:
        """Convert player state to dictionary representation.

        Provides both a nested structure for organized access and flattened
        common attributes for convenience.

        Returns:
            Dict[str, Any]: Dictionary containing all player state information
        """
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
            "name": self.name,
            "chips": self.chips,
            "bet": self.bet,
            "folded": self.folded,
            "position": str(self.position.value),
            "hand": str(self.hand) if self.hand else None,
            "hand_rank": str(self.hand_rank) if self.hand_rank else None,
            "has_acted": self.has_acted,
            "is_all_in": self.is_all_in,
            "is_active": self.is_active,
        }
