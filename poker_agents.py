import logging
import os
import random
import time
from typing import Any, Dict, List, Optional

import requests
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI API
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get logger
logger = logging.getLogger(__name__)


class PokerAgent:
    """Advanced poker agent with perception, reasoning, communication, and action capabilities.

    A sophisticated AI poker player that combines game state perception, strategic communication,
    and decision-making abilities to play Texas Hold'em poker.

    Attributes:
        name (str): Unique identifier for the agent
        model_type (str): Type of language model to use ('gpt' or 'local_llm')
        last_message (str): Most recent message sent by the agent
        perception_history (list): Historical record of game states and opponent actions
        strategy_style (str): Agent's playing style (e.g., 'Aggressive Bluffer', 'Calculated and Cautious')
    """

    def __init__(
        self, name: str, model_type: str = "gpt", strategy_style: Optional[str] = None
    ) -> None:
        self.name: str = name
        self.model_type: str = model_type
        self.last_message: str = ""
        self.perception_history: List[Dict[str, Any]] = []
        self.strategy_style: str = strategy_style or random.choice(
            [
                "Aggressive Bluffer",
                "Calculated and Cautious",
                "Chaotic and Unpredictable",
            ]
        )

    def perceive(
        self, game_state: Dict[str, Any], opponent_message: str
    ) -> Dict[str, Any]:
        """Process and store current game state and opponent's message.

        Args:
            game_state (dict): Current state of the poker game
            opponent_message (str): Message received from the opponent

        Returns:
            dict: Perception data including game state, opponent message, and timestamp
        """
        perception = {
            "game_state": game_state,
            "opponent_message": opponent_message,
            "timestamp": time.time(),
        }
        self.perception_history.append(perception)
        return perception

    def get_message(self, game_state: Dict[str, Any]) -> str:
        """Generate strategic communication based on game state and strategy style.

        Uses LLM to create contextually appropriate messages that align with the agent's
        strategy style and current game situation.

        Args:
            game_state (dict): Current state of the poker game

        Returns:
            str: Strategic message to influence opponent
        """
        prompt = f"""
        You are a {self.strategy_style} poker player in Texas Hold'em.
        
        Current situation:
        Game State: {game_state}
        Your recent observations: {self.perception_history[-3:] if len(self.perception_history) > 0 else "None"}
        
        Generate a strategic message to influence your opponent. Your personality is {self.strategy_style}.
        
        Your message should:
        1. Match your strategy style
        2. Be under 10 words
        3. Try to influence your opponent's next decision
        4. Consider your previous interactions
        
        What message will you send?
        """
        self.last_message = self._query_llm(prompt).strip()
        return self.last_message

    def interpret_message(self, opponent_message: str) -> str:
        """Enhanced message interpretation with historical context.

        Analyzes opponent messages considering recent game history and agent's strategy style.

        Args:
            opponent_message (str): Message received from the opponent

        Returns:
            str: Interpretation result ('trust', 'ignore', or 'counter-bluff')
        """
        recent_history = self.perception_history[-3:] if self.perception_history else []

        prompt = f"""
        You are a {self.strategy_style} poker player.
        Opponent's message: '{opponent_message}'
        Recent game history: {recent_history}
        
        Based on your strategy style and the game history:
        1. Analyze if they are bluffing, truthful, or misleading
        2. Consider their previous behavior patterns
        3. Think about how this fits your strategy style
        
        Respond with only: 'trust', 'ignore', or 'counter-bluff'
        """
        return self._query_llm(prompt).strip().lower()

    def get_action(
        self, game_state: Dict[str, Any], opponent_message: Optional[str] = None
    ) -> str:
        """Strategic action decision incorporating game history and style.

        Determines optimal poker action based on current game state, opponent behavior,
        and agent's strategy style.

        Args:
            game_state (dict): Current state of the poker game
            opponent_message (str, optional): Message received from opponent. Defaults to None.

        Returns:
            str: Chosen action ('fold', 'call', or 'raise')
        """
        recent_history = self.perception_history[-3:] if self.perception_history else []

        prompt = f"""
        You are a {self.strategy_style} poker player in a crucial moment.
        
        Current situation:
        Game State: {game_state}
        Opponent's Message: '{opponent_message or "nothing"}'
        Recent History: {recent_history}
        
        Consider:
        1. Your strategy style: {self.strategy_style}
        2. The opponent's recent behavior
        3. Your position and chip stack
        4. The credibility of their message
        
        Choose your action. Respond with only: 'fold', 'call', or 'raise'
        """
        return self._query_llm(prompt).strip().lower()

    def _query_llm(self, prompt: str) -> str:
        """Enhanced LLM query with error handling, retries, and logging.

        Makes API calls to either GPT or local LLM with built-in retry mechanism
        and comprehensive error handling.

        Args:
            prompt (str): Input prompt for the language model

        Returns:
            str: Model's response text

        Raises:
            Exception: If all retry attempts fail, returns 'fold' as fallback
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info("\n[LLM Query] Attempt %d for %s", attempt + 1, self.name)
                logger.debug("[LLM Query] Prompt: %s", prompt)

                if self.model_type == "gpt":
                    logger.info("[LLM Query] Using GPT model...")
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system",
                                "content": f"You are a {self.strategy_style} poker player.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=20,
                        temperature=0.7,
                    )
                    result = response.choices[0].message.content
                    logger.info("[LLM Query] Response: %s", result)
                    return result

                elif self.model_type == "local_llm":
                    logger.info("[LLM Query] Using Local LLM...")
                    endpoint = os.getenv("LOCAL_LLM_ENDPOINT")
                    logger.debug("[LLM Query] Endpoint: %s", endpoint)

                    response = requests.post(
                        endpoint,
                        json={"prompt": prompt, "max_tokens": 20},
                        timeout=5,
                    )
                    result = response.json()["choices"][0]["text"]
                    logger.info("[LLM Query] Response: %s", result)
                    return result

            except Exception as e:
                logger.error("[LLM Query] Error on attempt %d: %s", attempt + 1, str(e))
                logger.debug("[LLM Query] Error type: %s", type(e).__name__)
                if hasattr(e, "response"):
                    logger.error(
                        "[LLM Query] Response status: %d", e.response.status_code
                    )
                    logger.error("[LLM Query] Response body: %s", e.response.text)

                if attempt == max_retries - 1:
                    logger.warning(
                        "[LLM Query] All attempts failed for %s. Defaulting to 'fold'",
                        self.name,
                    )
                    return "fold"
                time.sleep(1)  # Wait before retry

    def update_strategy(self, game_outcome: Dict[str, Any]) -> None:
        """Update agent's strategy based on game outcomes and performance.

        Analyzes game results to potentially adjust strategy style and decision-making
        patterns for future games.

        Args:
            game_outcome (dict): Results and statistics from the completed game
        """
        prompt = f"""
        You are a poker player analyzing your performance.
        
        Game outcome: {game_outcome}
        Current strategy: {self.strategy_style}
        Recent history: {self.perception_history[-5:] if self.perception_history else "None"}
        
        Should you:
        1. Keep current strategy: {self.strategy_style}
        2. Switch to "Aggressive Bluffer"
        3. Switch to "Calculated and Cautious"
        4. Switch to "Chaotic and Unpredictable"
        
        Respond with just the number (1-4).
        """

        response = self._query_llm(prompt).strip()

        strategy_map = {
            "2": "Aggressive Bluffer",
            "3": "Calculated and Cautious",
            "4": "Chaotic and Unpredictable",
        }

        if response in strategy_map:
            logger.info(
                "[Strategy Update] %s changing strategy from %s to %s",
                self.name,
                self.strategy_style,
                strategy_map[response],
            )
            self.strategy_style = strategy_map[response]

    def analyze_opponent(self) -> Dict[str, Any]:
        """Analyze opponent's behavior patterns and tendencies.

        Reviews perception history to identify patterns in opponent's actions,
        messages, and betting behavior.

        Returns:
            dict: Analysis results including behavior patterns and threat assessment
        """
        if not self.perception_history:
            return {"patterns": "insufficient data", "threat_level": "unknown"}

        prompt = f"""
        Analyze this opponent's behavior patterns:
        Recent history: {self.perception_history[-5:]}
        
        Provide a concise analysis in this exact JSON format:
        {{
            "patterns": "<one word>",
            "threat_level": "<low/medium/high>"
        }}
        """

        try:
            response = self._query_llm(prompt).strip()
            # Basic validation that it's in the expected format
            if '"patterns"' in response and '"threat_level"' in response:
                return eval(
                    response
                )  # Safe here since we control the LLM output format
        except Exception as e:
            logger.error("[Opponent Analysis] Error parsing LLM response: %s", str(e))

        return {"patterns": "unknown", "threat_level": "medium"}

    def reset_state(self) -> None:
        """Reset agent's state for a new game.

        Clears perception history while maintaining strategy style and name.
        """
        self.perception_history = []
        self.last_message = ""
        logger.info("[Reset] Agent %s reset for new game", self.name)

    def get_stats(self) -> Dict[str, Any]:
        """Retrieve agent's performance statistics and current state.

        Returns:
            dict: Statistics including strategy style, perception history length,
                  and other relevant metrics
        """
        return {
            "name": self.name,
            "strategy_style": self.strategy_style,
            "perception_history_length": len(self.perception_history),
            "model_type": self.model_type,
            "last_message": self.last_message,
        }
