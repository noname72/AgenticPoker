from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import BaseModel

from data.types.player_types import PlayerPosition
from game.hand import Hand

if TYPE_CHECKING:
    from game import Player


class PlayerState(BaseModel):
    """Represents the complete state of a player in a poker game.

    This Pydantic model maintains all relevant information about a player during a poker game,
    including their current chips, betting status, position, hand information, and historical
    statistics. It provides serialization/deserialization and validation of player data.

    Attributes:
        name: Player's display name
        chips: Current chip count (must be >= 0)
        bet: Current bet amount in the pot (must be >= 0)
        folded: Whether the player has folded this hand
        hand: Player's cards
        position: Player's position at the table (enum)
        is_all_in: Whether player is all-in
        checked: Whether player has checked
        called: Whether player has called

    Methods:
        from_player: Create a PlayerState instance from a Player object.
            Args:
                player: The player instance to create state from
                private_attributes: Whether to include private attributes
        to_dict: Convert player state to a nested dictionary representation
        get: Dictionary-style attribute access with default value support
    """

    name: str
    chips: int
    bet: int
    folded: bool
    hand: Optional[Hand] = None
    position: PlayerPosition
    is_all_in: bool
    checked: bool
    called: bool

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
        return self.dict()

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_player(
        cls, player: "Player", private_attributes: bool = False
    ) -> "PlayerState":
        """Create a PlayerState instance from a Player object.

        Args:
            player: The player instance to create state from
            private_attributes: Whether to include private attributes

        Returns:
            PlayerState: A new PlayerState instance representing the player's current state
        """
        return cls(
            name=player.name,
            chips=player.chips,
            bet=player.bet,
            folded=player.folded,
            hand=player.hand if private_attributes else None,
            position=player.position,
            is_all_in=player.is_all_in,
            checked=player.checked,
            called=player.called,
        )
