import logging
import random
from typing import Any, Dict, List, Optional

from data.model import Game
from data.types.action_decision import ActionDecision, ActionType
from game.evaluator import HandEvaluation
from game.player import Player

logger = logging.getLogger(__name__)


class RandomAgent(Player):
    """A poker player that makes random decisions."""

    def __init__(self, name: str, chips: int = 1000):
        """Initialize the random agent."""
        super().__init__(name, chips)

    def decide_action(
        self, game: "Game", hand_eval: Optional[HandEvaluation] = None
    ) -> ActionDecision:
        """Randomly decide an action based on valid options.

        Args:
            game_state: Dictionary containing current game state
            opponent_message: Optional message from opponent (ignored for RandomAgent)

        Returns:
            ActionDecision: Action to take ('fold', 'call', or 'raise {amount}')
        """
        try:
            current_bet = game.current_bet

            # If we can't afford the current bet, fold
            if current_bet > self.chips:
                logger.info(f"{self.name} cannot afford current bet, folding")
                return ActionDecision(action_type=ActionType.FOLD)

            # Randomly choose between available actions
            actions = [ActionType.FOLD, ActionType.CALL]

            # Only add raise as an option if we have enough chips
            min_raise = current_bet * 2  # Minimum raise is typically 2x current bet
            if self.chips >= min_raise:
                actions.append(ActionType.RAISE)

            action = random.choice(actions)
            logger.info(f"{self.name} randomly decided to {action.value}")

            if action == ActionType.RAISE:
                # Calculate valid raise range
                max_raise = min(
                    self.chips, current_bet * 3
                )  # Limit to 3x current bet or all chips
                if max_raise > min_raise:
                    raise_amount = random.randrange(
                        min_raise, max_raise + 1, 10
                    )  # Step by 10 chips
                    logger.info(f"{self.name} raised to {raise_amount}")
                    return ActionDecision(
                        action_type=ActionType.RAISE, raise_amount=raise_amount
                    )

                logger.info(f"{self.name} raised to {min_raise}, falling back to call")
                return ActionDecision(action_type=ActionType.CALL)

            logger.info(f"{self.name} decided to call")
            return ActionDecision(action_type=ActionType.CALL)

        except Exception as e:
            logger.error(f"Random decision error: {str(e)}")
            return ActionDecision(action_type=ActionType.FOLD)  # Safe default action

    def get_message(self, game_state: str) -> str:
        """Return empty string as random agent doesn't communicate."""
        return ""

    def decide_draw(self) -> List[int]:
        """Randomly decide which cards to draw."""
        # Randomly discard 0-3 cards
        num_to_discard = random.randint(0, 3)
        if num_to_discard == 0:
            return []

        # Get random positions to discard
        positions = list(range(5))  # 5 card positions
        return sorted(random.sample(positions, num_to_discard))

    def perceive(self, game_state: str, opponent_message: str) -> Dict[str, Any]:
        """Do nothing as random agent doesn't track game state."""
        return {}

    def update_from_reward(self, reward: int, game_state: Dict[str, Any]) -> None:
        """Do nothing as random agent doesn't learn."""
        pass
