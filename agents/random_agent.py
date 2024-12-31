import logging
import random
from typing import Any, Dict, List, Optional, Union

from game.player import Player


class RandomAgent(Player):
    """A poker player that makes random decisions."""

    def __init__(self, name: str, chips: int = 1000):
        """Initialize the random agent."""
        super().__init__(name, chips)
        self.logger = logging.getLogger(__name__)

    def decide_action(
        self, 
        game_state: Dict,
        max_raises_reached: bool = False
    ) -> str:
        """Make a random decision to fold, call, or raise."""
        try:
            current_bet = game_state.get('current_bet', 0)
            call_amount = current_bet - self.bet
            
            if call_amount > self.chips:
                # Can't afford the call, must fold
                return "fold"
                
            # Randomly choose action with weights
            actions = []
            weights = []
            
            # Always allow fold
            actions.append("fold")
            weights.append(0.2)  # 20% chance to fold
            
            # Allow call if we have chips
            if self.chips >= call_amount:
                actions.append("call")
                weights.append(0.5)  # 50% chance to call
            
            # Allow raise if we have chips and max raises not reached
            if not max_raises_reached and self.chips > call_amount * 2:
                actions.append("raise")
                weights.append(0.3)  # 30% chance to raise
            
            action = random.choices(actions, weights=weights)[0]
            
            if action == "raise":
                # Random raise between min raise and max available
                min_raise = call_amount * 2
                max_raise = min(self.chips, call_amount * 4)
                raise_amount = random.randint(min_raise, max_raise)
                return f"raise {raise_amount}"
                
            return action
            
        except Exception as e:
            self.logger.error(f"Random decision error: {str(e)}")
            # Default to calling if possible, otherwise fold
            return "call" if self.chips >= call_amount else "fold"

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
