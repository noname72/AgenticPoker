from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from data.types.player_types import PlayerPosition


class SidePotMetrics(BaseModel):
    """Metrics for a side pot in the game."""

    amount: int = Field(description="Amount of chips in the side pot")
    eligible_players: int = Field(
        description="Number of players eligible for this side pot"
    )


class GameMetrics(BaseModel):
    """Metrics extracted from game state for strategic decision making."""

    # Basic metrics
    stack_size: int = Field(default=0, description="Current player's chip count")
    pot_size: int = Field(default=0, description="Current size of the main pot")
    position: PlayerPosition = Field(
        description="Player's position at the table"
    )
    phase: str = Field(description="Current game phase")
    players_remaining: int = Field(description="Number of active players still in hand")
    min_bet: int = Field(default=0, description="Minimum allowed bet amount")
    current_bet: int = Field(
        default=0, description="Current bet amount that needs to be called"
    )

    # Derived metrics
    pot_odds: float = Field(default=0.0, description="Ratio of current bet to pot size")
    stack_to_pot: float = Field(
        default=float("inf"), description="Ratio of stack size to pot"
    )

    # Optional side pot information
    side_pots: Optional[List[SidePotMetrics]] = Field(
        default=None, description="Information about side pots if they exist"
    )

    class Config:
        arbitrary_types_allowed = True
