import logging
import time
from typing import Dict, List, Optional

from game.player import Player

logger = logging.getLogger(__name__)


class BaseAgent(Player):
    """Base class for all poker agents, providing core player functionality."""

    def __init__(
        self,
        name: str,
        chips: int = 1000,
    ) -> None:
        super().__init__(name, chips)
        self.logger = logging.getLogger(__name__)

    def decide_action(
        self, game_state: str, opponent_message: Optional[str] = None
    ) -> str:
        """Base method for deciding actions."""
        return "call"  # Default safe action instead of raising NotImplementedError

    def get_message(self, game_state: str) -> str:
        """Base method for generating messages."""
        return ""

    def decide_draw(self) -> List[int]:
        """Base method for deciding which cards to draw."""
        return []

    def perceive(self, game_state: str, opponent_message: Optional[str] = None) -> Dict:
        """Base method for processing game state and opponent messages.

        Args:
            game_state (str): Current state of the game
            opponent_message (Optional[str]): Message from opponent, if any

        Returns:
            Dict: Perception data including game state and message
        """
        return {
            "game_state": game_state,
            "opponent_message": opponent_message,
            "timestamp": time.time(),
        }
