import logging
from typing import List, Optional

from poker_agents import PokerAgent

from .player import Player


class AIPlayer(Player):
    """
    AI-controlled poker player that uses LLM for decision making.

    Extends the base Player class with AI capabilities through a PokerAgent.
    The AI player can make strategic decisions, evaluate hands, and generate
    messages based on the current game state.

    Attributes:
        agent (PokerAgent): The AI agent handling decision making
        logger (Logger): Logger instance for tracking AI decisions
    """

    def __init__(
        self, name: str, chips: int = 1000, strategy_style: Optional[str] = None
    ) -> None:
        """
        Initialize AI player with both Player and Agent capabilities.

        Args:
            name: Player's display name
            chips: Starting chip count (default: 1000)
            strategy_style: Optional playing style for the AI (e.g., "aggressive", "conservative")
        """
        super().__init__(name, chips)
        self.agent = PokerAgent(name=name, strategy_style=strategy_style)
        self.logger = logging.getLogger(__name__)

    def decide_action(
        self, game_state: str, opponent_message: Optional[str] = None
    ) -> str:
        """
        Get the AI's decision for the current game state.

        Args:
            game_state: String representation of current game state including:
                       - Current pot
                       - Player positions
                       - Betting history
            opponent_message: Optional message from opponent for context

        Returns:
            str: Action decision, one of:
                - 'fold': Give up the hand
                - 'call': Match the current bet
                - 'raise': Increase the betting amount

        Note:
            Enriches the game state with hand evaluation before making decision
        """
        # Enrich game state with hand evaluation
        hand_eval = self.hand.evaluate() if self.hand.cards else "No cards"
        enriched_state = f"{game_state}, Hand evaluation: {hand_eval}"

        # Update agent's perception of game state
        self.agent.perceive(enriched_state, opponent_message or "")

        # Get action from agent
        action = self.agent.get_action(enriched_state, opponent_message)
        self.logger.info(f"{self.name} decides to {action}")
        return action

    def get_message(self, game_state: str) -> str:
        """
        Get a strategic message from the AI agent.

        Args:
            game_state: Current game state including pot, positions, and betting history

        Returns:
            str: Strategic message based on the agent's personality and game state

        Note:
            Enriches the game state with current hand information if available
        """
        # Enrich game state with hand information if available
        if self.hand.cards:
            game_state = f"{game_state}, Hand: {self.hand.show()}"
        return self.agent.get_message(game_state)

    def decide_draw(self) -> List[int]:
        """
        Decide which cards to discard and draw new ones.

        Uses the AI agent to analyze the current hand and make strategic
        discard decisions based on potential hands and strategy style.

        Returns:
            List[int]: Indices (0-4) of cards to discard. Empty list means keep all cards.

        Note:
            Falls back to a simple pair-based strategy if AI decision parsing fails
            Considers:
            - Existing pairs
            - Potential straights/flushes
            - High cards
            - Agent's strategy style
        """
        # Convert hand state to string for LLM
        game_state = f"Hand: {self.hand.show()}"

        prompt = f"""
        You are a {self.agent.strategy_style} poker player.
        Current hand: {game_state}
        
        Which cards should you discard? Consider:
        1. Pairs or potential straights/flushes
        2. High cards worth keeping
        3. Your strategy style
        
        Respond with only the indices (0-4) of cards to discard, separated by spaces.
        Example: "0 2 4" to discard first, third, and last cards.
        Respond with "none" to keep all cards.
        """

        response = self.agent._query_llm(prompt).strip().lower()
        if response == "none":
            return []

        try:
            indices = [int(i) for i in response.split()]
            return [i for i in indices if 0 <= i <= 4]
        except:
            # If parsing fails, make a simple decision based on pairs
            ranks = [card.rank for card in self.hand.cards]
            return [i for i, rank in enumerate(ranks) if ranks.count(rank) == 1]
