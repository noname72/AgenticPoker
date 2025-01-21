import logging
from enum import Enum
from typing import Optional

from pydantic import BaseModel, validator

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    FOLD = "fold"
    CALL = "call"
    RAISE = "raise"
    CHECK = "check"


class ActionDecision(BaseModel):
    """
    Represents an action decision from an LLM agent.

    Attributes:
        action_type: The type of action to take
        raise_amount: The amount to raise, if applicable
        reasoning: The reasoning behind the action
    """

    action_type: ActionType
    raise_amount: Optional[int] = None
    reasoning: Optional[str] = None

    @validator("raise_amount")
    def validate_raise_amount(cls, v, values):
        if values.get("action_type") == ActionType.RAISE:
            if v is None:
                raise ValueError("raise_amount is required when action_type is raise")
            if v <= 0:
                raise ValueError("raise_amount must be positive")
        return v

    @classmethod
    def parse_llm_response(cls, response: str) -> "ActionDecision":
        """Parse LLM response string into an ActionDecision object.

        Args:
            response: Raw response string from LLM

        Returns:
            ActionDecision: Parsed and validated action decision

        Raises:
            ValueError: If response cannot be parsed into a valid action
        """
        if "DECISION:" not in response:
            logger.warning("[Action] No DECISION directive found in response")
            return cls(action_type=ActionType.CALL)

        # Extract reasoning if present (everything before DECISION:)
        pre_reasoning = (
            response.split("DECISION:")[0].strip() if "DECISION:" in response else None
        )

        # Extract action and post-reasoning from response
        action_part = response.split("DECISION:")[1].strip()

        # Handle reasoning after the action
        action_text = action_part
        post_reasoning = None
        if "REASONING:" in action_part:
            action_text, post_reasoning = action_part.split("REASONING:", 1)
            action_text = action_text.strip()
            post_reasoning = post_reasoning.strip()

        # Combine reasonings, preferring post-reasoning if both exist
        reasoning = post_reasoning if post_reasoning else pre_reasoning

        parts = action_text.lower().split()

        try:
            # Clean the action type of any trailing punctuation
            action_type = parts[0].rstrip(",")

            if action_type == "raise":
                try:
                    # Remove any trailing comma from the amount
                    amount_str = parts[1].rstrip(",")
                    amount = int(amount_str)
                    return cls(
                        action_type=ActionType.RAISE,
                        raise_amount=amount,
                        reasoning=reasoning,
                    )
                except (IndexError, ValueError):
                    logger.warning("[Action] Invalid raise format")
                    return cls(action_type=ActionType.CALL, reasoning=reasoning)
            else:
                return cls(action_type=ActionType(action_type), reasoning=reasoning)
        except ValueError:
            logger.warning(f"[Action] Invalid action '{parts[0]}', defaulting to call")
            return cls(action_type=ActionType.CALL, reasoning=reasoning)

    def __str__(self) -> str:
        """String representation of the action response.

        Returns:
            str: Human readable string showing action type, amount (if raise), and reasoning
        """
        base = f"Action: {self.action_type.value}"
        if self.action_type == ActionType.RAISE:
            base += f" {self.raise_amount}"
        if self.reasoning:
            base += f" - {self.reasoning}"
        return base
