import random
from typing import Any, Dict, List, Optional

import numpy as np

from game.player import Player


class NashAgent(Player):
    """
    A poker agent that implements an approximate Nash equilibrium strategy.

    This agent uses a combination of game theory principles and heuristics to make
    decisions in poker games. It maintains action values for different moves and
    uses softmax probability distributions to balance exploitation with exploration.

    Attributes:
        action_values (dict): Stores numerical values for each possible action
        learning_rate (float): Rate at which the agent updates its action values
        temperature (float): Controls exploration vs exploitation in softmax
        bluff_frequency (float): Base probability of executing a bluff
    """

    def __init__(self, name: str, chips: int = 1000) -> None:
        super().__init__(name, chips)
        self.action_values = {"fold": 0.0, "call": 0.0, "raise": 0.0}
        self.learning_rate = 0.1  # Optional: For evolving weights
        self.temperature = 0.8  # Softmax temperature for probabilities
        self.bluff_frequency = 0.3  # Bluffing probability

    def decide_action(
        self, game_state: str, opponent_message: Optional[str] = None
    ) -> str:
        """
        Determines the next poker action using weighted probabilities.

        Uses pot odds and current game state to adjust action weights, then applies
        softmax normalization to select between folding, calling, or raising.

        Args:
            game_state: String representation of the current game state
            opponent_message: Optional message from the opponent

        Returns:
            str: Selected action ('fold', 'call', or 'raise')
        """
        # Example heuristic: Adjust weights based on game state
        bet_size = self._extract_bet_size(game_state)
        pot_size = self._extract_pot_size(game_state)
        if bet_size and pot_size:
            pot_odds = bet_size / (pot_size + bet_size)
            self.action_values["fold"] = (
                0.2 + pot_odds
            )  # Avoid folding with better pot odds
            self.action_values["call"] = (
                0.5 - pot_odds
            )  # Call more often if pot odds are favorable
            self.action_values["raise"] = 0.3  # Static raise probability for balance

        # Apply softmax for probabilistic decisions
        probabilities = self._softmax(self.action_values)
        return random.choices(list(self.action_values.keys()), weights=probabilities)[0]

    def decide_draw(self) -> List[int]:
        """
        Determines which cards to discard during the draw phase.

        Uses a simple value-based heuristic to keep the highest ranking cards
        and discard the lowest ones.

        Returns:
            List[int]: Indices of cards to discard (0-4)
        """
        hand = self.get_hand()  # Assuming this method returns a list of cards
        card_values = [card.rank for card in hand]
        return sorted(range(len(hand)), key=lambda i: card_values[i])[
            :3
        ]  # Keep top 2 cards

    def update_from_reward(self, reward: int, game_state: Dict[str, Any]) -> None:
        """
        Optional: Adjust action values based on rewards using a simple TD learning rule.
        """
        max_future_value = max(self.action_values.values())
        for action in self.action_values:
            self.action_values[action] += self.learning_rate * (
                reward + max_future_value - self.action_values[action]
            )

    def get_message(self, game) -> str:
        """
        Generate a strategic message to maintain unpredictability.
        """
        return random.choice(
            ["I think I've got this.", "Hmmm... Let's see.", "Your move."]
        )

    def perceive(self, game_state: str, opponent_message: str) -> Dict[str, Any]:
        """
        Process game state and opponent messages (minimal modeling).
        """
        return {"game_state": game_state, "opponent_message": opponent_message}

    def _extract_bet_size(self, game_state: str) -> Optional[int]:
        """Extract bet size from game state (placeholder)."""
        try:
            return int(game_state.split("Current bet: $")[1].split()[0])
        except:
            return None

    def _extract_pot_size(self, game_state: str) -> Optional[int]:
        """Extract pot size from game state (placeholder)."""
        try:
            return int(game_state.split("Pot size: $")[1].split()[0])
        except:
            return None

    def _softmax(self, values: Dict[str, float]) -> List[float]:
        """
        Converts action values to probabilities using softmax normalization.

        Applies temperature-controlled softmax function to create a probability
        distribution over possible actions.

        Args:
            values: Dictionary mapping actions to their numerical values

        Returns:
            List[float]: Normalized probabilities for each action
        """
        value_array = np.array(list(values.values()))
        exp_values = np.exp((value_array - np.max(value_array)) / self.temperature)
        return exp_values / exp_values.sum()

    def get_stats(self) -> Dict[str, Any]:
        """Return current agent statistics."""
        return {
            "name": self.name,
            "chips": self.chips,
            "action_values": self.action_values,
            "bluff_frequency": self.bluff_frequency,
        }
