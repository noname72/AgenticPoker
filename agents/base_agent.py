import logging
import time
from typing import Dict, List, Optional, Any

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
        self, game_state: Dict[str, Any], opponent_message: Optional[str] = None
    ) -> str:
        """Base method for deciding actions.
        
        Args:
            game_state: Dictionary containing current game state
            opponent_message: Optional message from opponent
            
        Returns:
            str: Action to take ('fold', 'call', or 'raise {amount}')
        """
        try:
            # Convert game state to string if needed
            if isinstance(game_state, dict):
                current_bet = game_state.get('current_bet', 0)
                pot = game_state.get('pot', 0)
                
                # Default to call if we can afford it, otherwise fold
                if self.chips >= current_bet:
                    return "call"
                return "fold"
            else:
                # Handle string game states (legacy support)
                return "call"
                
        except Exception as e:
            self.logger.error(f"Decision error: {str(e)}")
            return "fold"  # Safe default action

    def get_message(self, game_state: Dict[str, Any]) -> str:
        """Base method for generating messages.
        
        Args:
            game_state: Dictionary containing current game state
            
        Returns:
            str: Empty string (base agents don't chat)
        """
        return ""

    def decide_draw(self) -> List[int]:
        """Base method for deciding which cards to draw.
        
        Returns:
            List[int]: Empty list (base agents don't draw)
        """
        return []

    def perceive(
        self, 
        game_state: Dict[str, Any], 
        opponent_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process game state and opponent messages.
        
        Args:
            game_state: Dictionary containing current game state
            opponent_message: Optional message from opponent
            
        Returns:
            Dict: Perception data including game state and message
        """
        try:
            # Ensure game_state is properly formatted
            if isinstance(game_state, dict):
                perception = {
                    "game_state": game_state,
                    "opponent_message": opponent_message,
                    "timestamp": time.time()
                }
            else:
                # Convert string game state to dict format
                perception = {
                    "game_state": {"raw": str(game_state)},
                    "opponent_message": opponent_message,
                    "timestamp": time.time()
                }
            return perception
            
        except Exception as e:
            self.logger.error(f"Perception error: {str(e)}")
            return {
                "game_state": {},
                "opponent_message": None,
                "timestamp": time.time(),
                "error": str(e)
            }
