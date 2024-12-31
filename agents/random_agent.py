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
        self, game_state: Dict[str, Any], opponent_message: Optional[str] = None
    ) -> str:
        """Make a random decision."""
        try:
            # Extract current bet from game state
            current_bet = game_state.get('current_bet', 0)
            
            # List of possible actions based on current chips
            possible_actions = ['fold']
            
            # Can only call if we have enough chips
            if self.chips >= current_bet:
                possible_actions.append('call')
                
                # Can only raise if we have more than the current bet
                if self.chips > current_bet:
                    # Random raise amount between current bet and max possible
                    max_raise = min(self.chips, current_bet * 3)  # Limit raise to 3x
                    if max_raise > current_bet:
                        raise_amount = random.randint(current_bet, max_raise)
                        possible_actions.append(f'raise {raise_amount}')

            # Choose random action from possible actions
            return random.choice(possible_actions)

        except Exception as e:
            self.logger.error(f"Random decision error: {str(e)}")
            return "fold"  # Safe default

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
