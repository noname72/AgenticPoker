import random
from typing import Any, Dict, List, Optional

from game.player import Player


class RandomAgent(Player):
    """A poker agent that makes completely random decisions.

    This agent serves as a control/baseline to compare against LLM-powered agents.
    It makes all decisions randomly without any strategy or reasoning.
    """

    def __init__(self, name: str, chips: int = 1000) -> None:
        super().__init__(name, chips)
        self.action_weights = {
            "fold": 0.2,  # 20% chance to fold
            "call": 0.5,  # 50% chance to call
            "raise": 0.3,  # 30% chance to raise
        }

    def decide_action(
        self, game_state: str, opponent_message: Optional[str] = None
    ) -> str:
        """Make a random decision weighted by action_weights."""
        return random.choices(
            list(self.action_weights.keys()), weights=list(self.action_weights.values())
        )[0]

    def get_message(self, game_state: str) -> str:
        """Return empty string as random agent doesn't communicate."""
        return ""

    def decide_draw(self) -> List[int]:
        """Randomly decide which cards to discard (0-3 cards)."""
        num_cards = random.randint(0, 3)  # Randomly discard 0-3 cards
        if num_cards == 0:
            return []
        return random.sample(range(5), num_cards)

    def perceive(self, game_state: str, opponent_message: str) -> Dict[str, Any]:
        """Do nothing as random agent doesn't track game state."""
        return {}

    def update_from_reward(self, reward: int, game_state: Dict[str, Any]) -> None:
        """Do nothing as random agent doesn't learn."""
        pass
