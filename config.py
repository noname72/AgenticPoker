from typing import Dict, Optional


class GameConfig:
    """Configuration for poker game settings."""

    def __init__(
        self,
        small_blind: int = 10,
        big_blind: int = 20,
        ante: int = 0,
        session_id: Optional[str] = None,
        starting_chips: int = 1000,
        max_rounds: Optional[int] = None,
        min_bet: int = 20,
    ):
        # Game settings passed in constructor
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.ante = ante
        self.session_id = session_id
        self.starting_chips = starting_chips
        self.max_rounds = max_rounds
        self.min_bet = min_bet

        # Database settings
        self.DATABASE_URL: str = "sqlite:///poker_game.db"

        # Game defaults
        self.MIN_PLAYERS: int = 2
        self.MAX_PLAYERS: int = 10

        # Timing settings
        self.DECISION_TIMEOUT: int = 30  # seconds
        self.ROUND_TIMEOUT: int = 300  # seconds

        # AI settings
        self.AI_CONFIDENCE_THRESHOLD: float = 0.7

        # Betting limits
        self.MIN_RAISE: int = 20
        self.MAX_RAISE_MULTIPLIER: int = 4  # max raise = current_bet * multiplier

    class Config:
        env_file = ".env"
