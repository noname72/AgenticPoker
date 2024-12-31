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
        game_state: Dict[str, Any],
        opponent_message: Optional[str] = None
    ) -> str:
        """Randomly decide an action based on valid options.
        
        Args:
            game_state: Dictionary containing current game state
            opponent_message: Optional message from opponent (ignored for RandomAgent)
            
        Returns:
            str: Action to take ('fold', 'call', or 'raise {amount}')
        """
        try:
            if isinstance(game_state, dict):
                current_bet = game_state.get("current_bet", 0)
                pot = game_state.get("pot", 0)
                
                # If we can't afford the current bet, fold
                if current_bet > self.chips:
                    return "fold"
                    
                # Randomly choose between available actions
                actions = ["fold", "call"]
                
                # Only add raise as an option if we have enough chips
                min_raise = current_bet * 2  # Minimum raise is typically 2x current bet
                if self.chips >= min_raise:
                    actions.append("raise")
                
                action = random.choice(actions)
                
                if action == "raise":
                    # Calculate valid raise range
                    max_raise = min(self.chips, current_bet * 3)  # Limit to 3x current bet or all chips
                    if max_raise > min_raise:
                        raise_amount = random.randrange(min_raise, max_raise + 1, 10)  # Step by 10 chips
                        return f"raise {raise_amount}"
                    return "call"  # Fall back to call if raise range is invalid
                    
                return action
                
            return "fold"  # Default to fold for invalid game state
            
        except Exception as e:
            self.logger.error(f"Random decision error: {str(e)}")
            return "fold"  # Safe default action

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
