from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from data.states.player_state import PlayerState
from data.states.round_state import RoundState
from data.types.base_types import DeckState
from data.types.player_types import PlayerPosition
from data.types.pot_types import PotState

if TYPE_CHECKING:
    from game.game import AgenticPoker


class GameState(BaseModel):
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

    # Required fields
    players: List[PlayerState]
    dealer_position: int
    small_blind: int
    big_blind: int
    ante: int
    min_bet: int
    round_state: RoundState
    pot_state: PotState
    deck_state: DeckState

    # Optional fields with defaults
    active_player_position: Optional[int] = None
    max_raise_multiplier: int = Field(default=3, gt=0)
    max_raises_per_round: int = Field(default=4, gt=0)

    @validator("players")
    def validate_players(cls, v):
        if not v:
            raise ValueError("Players list cannot be empty")
        return v

    @validator("small_blind", "big_blind", "ante", "min_bet")
    def validate_amounts(cls, v):
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return v

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
            Dict[str, Any]: Dictionary representation of the game state
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
            "players": [p.dict() for p in self.players],
            "positions": {
                "dealer": self.dealer_position,
                "active_player": self.active_player_position,
            },
            "round_state": {
                **self.round_state.dict(),
                "phase": str(self.round_state.phase),
            },
            "pot_state": self.pot_state.dict(),
            "deck_state": self.deck_state.dict(),
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

    @classmethod
    def from_game(cls, game: "AgenticPoker") -> "GameState":
        """Create a GameState instance from a Game object.

        Args:
            game (Game): The game instance to create state from

        Returns:
            GameState: A new GameState instance representing the current game state
        """
        players_count = len(game.players)
        player_states = []

        # Calculate blind positions
        sb_pos = (game.dealer_index + 1) % players_count
        bb_pos = (game.dealer_index + 2) % players_count

        # Process player states
        for i, player in enumerate(game.players):
            # Calculate position relative to dealer
            position_index = (i - game.dealer_index) % players_count
            position = {
                0: PlayerPosition.DEALER,
                1: PlayerPosition.SMALL_BLIND,
                2: PlayerPosition.BIG_BLIND,
                3: PlayerPosition.UNDER_THE_GUN,
                -1: PlayerPosition.CUTOFF,  # Second to last position
            }.get(position_index, PlayerPosition.MIDDLE)

            # Get player's current state
            player_state = player.get_state()

            # Update position-specific information
            player_state.position = position
            player_state.is_dealer = position == PlayerPosition.DEALER
            player_state.is_small_blind = position == PlayerPosition.SMALL_BLIND
            player_state.is_big_blind = position == PlayerPosition.BIG_BLIND

            player_states.append(player_state)

            # Update the player with their new state
            player.update_from_state(player_state)

        # Create or update round state if needed
        if not hasattr(game, "round_state"):
            game.round_state = RoundState.new_round(game.round_number)

        # Set positions in round state
        game.round_state.dealer_position = game.dealer_index
        game.round_state.small_blind_position = sb_pos
        game.round_state.big_blind_position = bb_pos
        game.round_state.first_bettor_index = (bb_pos + 1) % players_count

        # Calculate minimum raise based on current game state
        current_bet = getattr(game.round_state, "current_bet", game.big_blind)
        min_raise = max(
            game.config.min_bet,  # Configured minimum bet
            game.big_blind,  # Big blind amount
            current_bet,  # Current bet to match
        )

        # Update round state with current pot info
        game.round_state.main_pot = game.pot_manager.pot
        game.round_state.side_pots = [
            {
                "amount": pot.amount,
                "eligible_players": [p.name for p in pot.eligible_players],
            }
            for pot in (game.pot_manager.side_pots or [])
        ]

        return cls(
            small_blind=game.small_blind,
            big_blind=game.big_blind,
            ante=game.ante,
            min_bet=min_raise,
            max_raise_multiplier=game.config.max_raise_multiplier,
            max_raises_per_round=game.config.max_raises_per_round,
            players=player_states,
            dealer_position=game.dealer_index,
            active_player_position=(
                game.active_player_position
                if hasattr(game, "active_player_position")
                else None
            ),
            round_state=game.round_state,
            pot_state=game.pot_manager.get_state(),
            deck_state=game.deck.get_state(),
        )

    class Config:
        arbitrary_types_allowed = True
