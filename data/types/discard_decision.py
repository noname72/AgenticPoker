import re
from typing import List, Optional

from pydantic import BaseModel, validator


class DiscardDecision(BaseModel):
    """Represents a discard decision with reasoning.

    Attributes:
        discard: List of card positions to discard (0-4), or None if keeping all cards
        reasoning: Explanation for the discard decision
    """

    discard: Optional[List[int]] = None
    reasoning: Optional[str] = None

    @validator("discard")
    def validate_discard(cls, v):
        if v is not None:
            if not all(0 <= x <= 4 for x in v):
                raise ValueError("Discard positions must be between 0 and 4")
            if len(v) > 3:
                raise ValueError("Cannot discard more than 3 cards")
            if len(v) != len(set(v)):
                raise ValueError("Duplicate discard positions not allowed")
        return v

    @classmethod
    def parse_llm_response(cls, response: str) -> "DiscardDecision":
        """Parse LLM response string into a DiscardDecision object.

        Args:
            response: Raw response string from LLM

        Returns:
            DiscardDecision: Parsed and validated discard decision

        Raises:
            ValueError: If response cannot be parsed into a valid discard decision
        """
        discard_match = re.search(
            r"DISCARD:\s*(\[[\d,\s]*\]|none)", response, re.IGNORECASE
        )
        reasoning_match = re.search(r"REASONING:\s*(.+)", response, re.IGNORECASE)

        if not discard_match:
            raise ValueError("No valid DISCARD directive found")

        discard_str = discard_match.group(1).lower().strip()
        reasoning = reasoning_match.group(1).strip() if reasoning_match else None

        if discard_str == "none":
            return cls(discard=None, reasoning=reasoning)

        try:
            # Extract numbers from bracket format [x,y,z]
            numbers = [int(n) for n in re.findall(r"\d+", discard_str)]
            return cls(discard=numbers, reasoning=reasoning)
        except ValueError:
            raise ValueError("Invalid discard format")

    def __str__(self) -> str:
        """String representation of the discard decision."""
        if self.discard is None:
            discard_str = "Keep all cards"
        else:
            discard_str = f"Discard positions {self.discard}"

        if self.reasoning:
            return f"{discard_str} - {self.reasoning}"
        return discard_str
