import json
import logging
from typing import Any, Dict

from pydantic import BaseModel, Field, validator

from data.types.plan import Approach, BetSizing

logger = logging.getLogger(__name__)


class PlanResponse(BaseModel):
    """Pydantic model for validating LLM responses to planning prompts."""

    approach: Approach = Field(
        ..., description="Strategic approach (aggressive/balanced/defensive/deceptive)"
    )
    reasoning: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="Explanation of the strategic plan",
    )
    bet_sizing: BetSizing = Field(
        ..., description="Betting size strategy (small/medium/large)"
    )
    bluff_threshold: float = Field(
        ..., ge=0.0, le=1.0, description="Probability threshold for bluffing decisions"
    )
    fold_threshold: float = Field(
        ..., ge=0.0, le=1.0, description="Probability threshold for folding decisions"
    )

    @validator("reasoning")
    def validate_reasoning(cls, v: str) -> str:
        """Ensure reasoning is meaningful and not just whitespace."""
        if not v.strip():
            raise ValueError("Reasoning cannot be empty or just whitespace")
        return v.strip()

    @validator("bluff_threshold", "fold_threshold")
    def validate_thresholds(cls, v: float) -> float:
        """Additional validation for threshold values."""
        if not isinstance(v, (int, float)):
            raise ValueError("Threshold must be a number")
        return float(v)

    @classmethod
    def parse_llm_response(cls, response: str) -> Dict[str, Any]:
        """Parse and validate LLM response into plan data.

        Args:
            response: Raw response string from LLM containing JSON plan data

        Returns:
            Dict[str, Any]: Validated plan data with default values if parsing fails
        """
        try:
            # Parse JSON and validate with Pydantic model
            raw_data = json.loads(response.strip())
            validated_data = cls(**raw_data)
            return validated_data.dict()
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse/validate LLM response: {str(e)}")
            logger.debug(f"Invalid response: {response}")
            # Return default plan data on parse error
            return {
                "approach": "balanced",
                "reasoning": "Default plan due to parse error",
                "bet_sizing": "medium",
                "bluff_threshold": 0.5,
                "fold_threshold": 0.3,
            }

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "approach": "aggressive",
                "reasoning": "High card with potential to bluff",
                "bet_sizing": "medium",
                "bluff_threshold": 0.6,
                "fold_threshold": 0.3,
            }
        }
