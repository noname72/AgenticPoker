from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from data.types.base_types import DeckState
from data.types.player_types import PlayerState
from data.types.pot_types import PotState
from data.types.round_state import RoundState


@dataclass
class GameState:
    """Represents the complete state of a poker game.

    This class encapsulates all information about the current state of a poker game,
    including player states, positions, betting information, and game configuration.

    Attributes:
        players (List[PlayerState]): List of player states in the game
        dealer_position (int): Position index of the dealer button
        small_blind (int): Amount of the small blind
        big_blind (int): Amount of the big blind
        ante (int): Amount of the ante, if any
        min_bet (int): Minimum bet amount allowed
        round_state (RoundState): Current state of the betting round
        pot_state (PotState): State of the pot(s)
        deck_state (DeckState): Current state of the deck
        active_player_position (Optional[int]): Position index of the currently active player
        max_raise_multiplier (int): Maximum multiplier for raises (default: 3)
        max_raises_per_round (int): Maximum number of raises allowed per round (default: 4)
    """

    # Required fields (no defaults)
    players: List[PlayerState]
    dealer_position: int
    small_blind: int
    big_blind: int
    ante: int
    min_bet: int
    round_state: RoundState
    pot_state: PotState
    deck_state: DeckState

    # Optional fields (with defaults)
    active_player_position: Optional[int] = None
    max_raise_multiplier: int = 3
    max_raises_per_round: int = 4

    def copy(self) -> "GameState":
        """Create a deep copy of the game state.

        Returns:
            GameState: A new GameState instance with all fields deeply copied
        """
        return deepcopy(self)

    def to_dict(self) -> Dict[str, Any]:
        """Convert game state to dictionary representation.

        Creates a dictionary containing all relevant game state information,
        including configuration, player states, positions, round state, and pot state.

        Returns:
            Dict[str, Any]: Dictionary representation of the game state with the following structure:
                - config: Dictionary of game configuration parameters
                - players: List of player state dictionaries
                - positions: Dictionary of dealer and active player positions
                - round_state: Dictionary of current round state
                - pot_state: Dictionary of pot state
                - deck_state: Dictionary of deck state
                - pot: Main pot amount (for backward compatibility)
                - current_bet: Current bet amount in the round
        """
        return {
            "config": {
                "small_blind": self.small_blind,
                "big_blind": self.big_blind,
                "ante": self.ante,
                "min_bet": self.min_bet,
                "max_raise_multiplier": self.max_raise_multiplier,
                "max_raises_per_round": self.max_raises_per_round,
            },
            "players": [p.to_dict() for p in self.players],
            "positions": {
                "dealer": self.dealer_position,
                "active_player": self.active_player_position,
            },
            "round_state": {
                **self.round_state.to_dict(),
                "phase": str(self.round_state.phase),
            },
            "pot_state": self.pot_state.to_dict(),
            "deck_state": self.deck_state.to_dict(),
            # Add pot directly at top level for backward compatibility
            "pot": self.pot_state.main_pot,
            "current_bet": (
                self.round_state.current_bet
                if hasattr(self.round_state, "current_bet")
                else 0
            ),
        }

    def __getitem__(self, key: str) -> Any:
        """Enable dictionary-style access to game state attributes.

        Args:
            key (str): Name of the attribute to access

        Returns:
            Any: Value of the requested attribute

        Raises:
            KeyError: If the key doesn't exist in either attributes or dictionary representation
        """
        if hasattr(self, key):
            return getattr(self, key)
        # Convert to dict for legacy dictionary access
        return self.to_dict()[key]

    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for checking if attributes exist.

        Args:
            key (str): Name of the attribute to check

        Returns:
            bool: True if the attribute exists, False otherwise
        """
        if hasattr(self, key):
            return True
        return key in self.to_dict()

    def get(self, key: str, default: Any = None) -> Any:
        """Implement dict-style .get() method.

        Args:
            key (str): Name of the attribute to access
            default (Any, optional): Default value to return if key doesn't exist. Defaults to None.

        Returns:
            Any: Value of the requested attribute or the default value if not found
        """
        try:
            return self[key]
        except (KeyError, AttributeError):
            return default
