from typing import Dict, Any
from pydantic import validator, ValidationError

from data.enums import GameType, ActionType, PlayerStatus, BettingRound
from data.dto import GameDTO, RoundActionDTO, GamePlayerAssociationDTO


class GameValidator:
    """Validators for game-related DTOs."""

    @validator("game_type")
    def validate_game_type(cls, v: str) -> str:
        if v not in GameType.__members__.values():
            raise ValueError(f"Invalid game type: {v}")
        return v

    @validator("small_blind", "big_blind", "ante")
    def validate_positive_integers(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Value must be non-negative")
        return v

    @validator("max_players")
    def validate_max_players(cls, v: int) -> int:
        if not (2 <= v <= 10):
            raise ValueError("Max players must be between 2 and 10")
        return v


class ActionValidator:
    """Validators for action-related DTOs."""

    @validator("action_type")
    def validate_action_type(cls, v: str) -> str:
        if v not in ActionType.__members__.values():
            raise ValueError(f"Invalid action type: {v}")
        return v

    @validator("amount")
    def validate_bet_amount(cls, v: int, values: Dict[str, Any]) -> int:
        if v < 0:
            raise ValueError("Bet amount must be non-negative")
        if values.get("action_type") in [ActionType.FOLD, ActionType.CHECK]:
            if v != 0:
                raise ValueError(f"Amount must be 0 for {values['action_type']}")
        return v
