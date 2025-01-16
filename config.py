from typing import Dict


class GameConfig:
    """Configuration for poker game settings."""

    # Database settings
    DATABASE_URL: str = "sqlite:///poker_game.db"

    # Game defaults
    DEFAULT_STARTING_CHIPS: int = 1000
    DEFAULT_SMALL_BLIND: int = 10
    DEFAULT_BIG_BLIND: int = 20
    DEFAULT_ANTE: int = 0
    MIN_PLAYERS: int = 2
    MAX_PLAYERS: int = 10

    # Timing settings
    DECISION_TIMEOUT: int = 30  # seconds
    ROUND_TIMEOUT: int = 300  # seconds

    # AI settings
    AI_CONFIDENCE_THRESHOLD: float = 0.7

    # Betting limits
    MIN_RAISE: int = 20
    MAX_RAISE_MULTIPLIER: int = 4  # max raise = current_bet * multiplier

    # Texas Holdem specific settings
    TEXAS_HOLDEM_STARTING_CHIPS: int = 2000
    TEXAS_HOLDEM_SMALL_BLIND: int = 25
    TEXAS_HOLDEM_BIG_BLIND: int = 50
    TEXAS_HOLDEM_ANTE: int = 5
    TEXAS_HOLDEM_MIN_RAISE: int = 50
    TEXAS_HOLDEM_MAX_RAISE_MULTIPLIER: int = 5

    class Config:
        env_file = ".env"
