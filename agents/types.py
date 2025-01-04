from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, validator
import time


class Approach(str, Enum):
    """Strategic approach types for poker gameplay."""

    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    DEFENSIVE = "defensive"
    DECEPTIVE = "deceptive"


class BetSizing(str, Enum):
    """Bet sizing categories."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class Plan(BaseModel):
    """Represents a strategic poker plan.

    A Plan encapsulates the strategic decisions and thresholds that guide
    an agent's poker play over a short time period.
    """

    approach: Approach
    reasoning: str
    bet_sizing: BetSizing
    bluff_threshold: float = Field(..., ge=0.0, le=1.0)
    fold_threshold: float = Field(..., ge=0.0, le=1.0)
    expiry: float
    adjustments: List[str] = Field(default_factory=list)
    target_opponent: Optional[str] = None

    class Config:
        frozen = True  # Makes the plan immutable
        json_encoders = {
            Approach: lambda v: v.value,
            BetSizing: lambda v: v.value,
        }

    def is_expired(self, current_time: float = None) -> bool:
        """Check if the plan has expired."""
        if current_time is None:
            current_time = time.time()
        return current_time > self.expiry

    def to_prompt(self) -> str:
        """Convert plan to a prompt-friendly string format."""
        adjustments_str = (
            "\n      * ".join(self.adjustments) if self.adjustments else "None"
        )

        return f"""Strategic Plan:
        - Approach: {self.approach.value}
        - Bet Sizing: {self.bet_sizing.value}
        - Bluff Threshold: {self.bluff_threshold:.1f}
        - Fold Threshold: {self.fold_threshold:.1f}
        - Reasoning: {self.reasoning}
        - Adjustments:
          * {adjustments_str}
        - Target Opponent: {self.target_opponent or 'None'}"""

    @classmethod
    def from_dict(cls, data: dict) -> "Plan":
        """Create a Plan instance from a dictionary."""
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert plan to dictionary format."""
        return self.dict()
