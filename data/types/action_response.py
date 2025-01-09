import logging
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    FOLD = "fold"
    CALL = "call"
    RAISE = "raise"


class ActionResponse(BaseModel):
    """
    Represents an action response from an LLM agent.

    Attributes:
        action_type: The type of action to take
        raise_amount: The amount to raise, if applicable
        reasoning: The reasoning behind the action
    """

    action_type: ActionType
    raise_amount: Optional[int] = None
    reasoning: str = Field(default="No reasoning provided")

    @validator("raise_amount")
    def validate_raise_amount(cls, v, values):
        if values.get("action_type") == ActionType.RAISE:
            if v is None:
                raise ValueError("raise_amount is required when action_type is raise")
            if v <= 0:
                raise ValueError("raise_amount must be positive")
        return v

    @classmethod
    def parse_llm_response(cls, response: str) -> "ActionResponse":
        """Parse LLM response string into an ActionResponse object.

        Args:
            response: Raw response string from LLM

        Returns:
            ActionResponse: Parsed and validated action response

        Raises:
            ValueError: If response cannot be parsed into a valid action
        """
        if "DECISION:" not in response:
            logger.warning("[Action] No DECISION directive found in response")
            return cls(action_type=ActionType.CALL)

        # Extract action from response
        action_text = response.split("DECISION:")[1].strip().lower()
        parts = action_text.split()

        try:
            if parts[0] == "raise":
                try:
                    amount = int(parts[1])
                    return cls(action_type=ActionType.RAISE, raise_amount=amount)
                except (IndexError, ValueError):
                    logger.warning("[Action] Invalid raise format")
                    return cls(action_type=ActionType.CALL)
            else:
                return cls(action_type=ActionType(parts[0]))
        except ValueError:
            logger.warning(f"[Action] Invalid action '{parts[0]}', defaulting to call")
            return cls(action_type=ActionType.CALL)
