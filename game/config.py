from dataclasses import dataclass
from typing import Optional


@dataclass
class GameConfig:
    """
    Configuration parameters for a poker game.

    This class defines all the customizable parameters that control game behavior,
    including betting limits, starting conditions, and round restrictions.

    Attributes:
        starting_chips (int): Initial chip amount for each player (default: 1000)
        small_blind (int): Small blind bet amount (default: 10)
        big_blind (int): Big blind bet amount (default: 20)
        ante (int): Mandatory bet required from all players before dealing (default: 0)
        max_rounds (Optional[int]): Maximum number of rounds to play, None for unlimited (default: None)
        session_id (Optional[str]): Unique identifier for the game session (default: None)
        game_type (str): Type of poker game ("FIVE_CARD_DRAW", "TEXAS_HOLDEM") (default: "FIVE_CARD_DRAW")
        max_players (int): Maximum number of players allowed in the game (default: 6)
        max_raise_multiplier (Optional[int]): Maximum raise as multiplier of current bet.
                                            None for no limit (TEXAS_HOLDEM). (default: None, 3 for FIVE_CARD_DRAW)
        max_raises_per_round (Optional[int]): Maximum number of raises allowed per betting round.
                                             None for no limit (TEXAS_HOLDEM). (default: None, 4 for FIVE_CARD_DRAW)
        min_bet (Optional[int]): Minimum bet amount, defaults to big blind if not specified

    Raises:
        ValueError: If any of the numerical parameters are invalid (negative or zero where not allowed)
    """

    starting_chips: int = 1000
    small_blind: int = 10
    big_blind: int = 20
    ante: int = 0
    max_rounds: Optional[int] = None
    session_id: Optional[str] = None
    game_type: str = "FIVE_CARD_DRAW"  # Possible values: "FIVE_CARD_DRAW", "TEXAS_HOLDEM"
    max_players: int = 6  # Maximum number of players allowed in the game
    max_raise_multiplier: Optional[int] = None
    max_raises_per_round: Optional[int] = None
    min_bet: Optional[int] = None

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.starting_chips <= 0:
            raise ValueError("Starting chips must be positive")
        if self.small_blind <= 0 or self.big_blind <= 0:
            raise ValueError("Blinds must be positive")
        if self.ante < 0:
            raise ValueError("Ante cannot be negative")
        if self.max_players < 2:
            raise ValueError("Maximum players must be at least 2")

        if self.game_type == "FIVE_CARD_DRAW":
            if self.max_raise_multiplier is None:
                self.max_raise_multiplier = 3
            if self.max_raises_per_round is None:
                self.max_raises_per_round = 4
        elif self.game_type == "TEXAS_HOLDEM":
            if self.max_raise_multiplier is not None:
                # In a real scenario, you might log a warning here
                # print(f"Warning: max_raise_multiplier is set for TEXAS_HOLDEM game type. It will be ignored.")
                self.max_raise_multiplier = None
            if self.max_raises_per_round is not None:
                # print(f"Warning: max_raises_per_round is set for TEXAS_HOLDEM game type. It will be ignored.")
                self.max_raises_per_round = None

        if self.game_type == "FIVE_CARD_DRAW": # These validations only apply to limit games
            if self.max_raise_multiplier is not None and self.max_raise_multiplier <= 0:
                raise ValueError("Max raise multiplier must be positive for FIVE_CARD_DRAW")
            if self.max_raises_per_round is not None and self.max_raises_per_round <= 0:
                raise ValueError("Max raises per round must be positive for FIVE_CARD_DRAW")

        # Set min_bet to big blind if not specified
        if self.min_bet is None:
            self.min_bet = self.big_blind
        elif self.min_bet < self.big_blind:
            raise ValueError("Minimum bet cannot be less than big blind")
