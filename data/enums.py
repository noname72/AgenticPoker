from enum import Enum


class GameType(str, Enum):
    """Valid poker game types."""

    FIVE_CARD_DRAW = "5-card-draw"
    TEXAS_HOLDEM = "texas-holdem"
    SEVEN_CARD_STUD = "7-card-stud"


class ActionType(str, Enum):
    """Valid poker actions."""

    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"
    ALL_IN = "all-in"


class PlayerStatus(str, Enum):
    """Player status in a game."""

    ACTIVE = "active"
    FOLDED = "folded"
    ALL_IN = "all-in"
    ELIMINATED = "eliminated"


class BettingRound(str, Enum):
    """Betting rounds in poker."""

    PRE_DRAW = "pre-draw"  # For 5-card draw
    POST_DRAW = "post-draw"
    PRE_FLOP = "pre-flop"  # For Hold'em
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
