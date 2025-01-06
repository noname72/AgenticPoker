import asyncio
import logging
import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

from agents.base_agent import BaseAgent
from agents.prompts import (
    DECISION_PROMPT,
    DISCARD_PROMPT,
    EXECUTION_PROMPT,
    INTERPRET_MESSAGE_PROMPT,
    MESSAGE_PROMPT,
    PLANNING_PROMPT,
    STRATEGIC_BANTER_PROMPT,
    STRATEGIC_MESSAGE_PROMPT,
)
from agents.strategy_cards import StrategyManager
from agents.strategy_planner import StrategyPlanner
from agents.types import Approach, BetSizing, Plan
from data.memory import ChromaMemoryStore
from exceptions import LLMError, OpenAIError
from game.types import GameState

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class LLMAgent(BaseAgent):
    """Advanced poker agent with LLM-powered decision making capabilities.

    An intelligent poker agent that uses Large Language Models (LLM) to make strategic decisions,
    generate messages, and adapt its gameplay based on the current situation. Features include
    planning, reasoning, reflection, and both short-term and long-term memory.

    Features:
        - Strategic planning with adaptive replanning
        - Chain-of-thought reasoning for decisions
        - Self-reflection on actions
        - Short-term memory for recent events
        - Long-term memory using ChromaDB
        - Personality traits and strategy styles
        - Message generation and interpretation
        - Error handling and retry mechanisms

    Attributes:
        name (str): Agent's identifier
        chips (int): Current chip count
        strategy_style (str): Current strategic approach
        personality_traits (dict): Numerical traits affecting decisions
        use_reasoning (bool): Enable chain-of-thought reasoning
        use_reflection (bool): Enable action reflection
        use_planning (bool): Enable strategic planning
        memory_store (ChromaMemoryStore): Long-term memory storage
        perception_history (list): Recent game events
        conversation_history (list): Recent messages
    """

    def __init__(
        self,
        name: str,
        chips: int = 1000,
        strategy_style: str = "Aggressive Bluffer",
        use_reasoning: bool = True,
        use_reflection: bool = True,
        use_planning: bool = True,
        use_opponent_modeling: bool = True,
        use_reward_learning: bool = False,
        learning_rate: float = 0.1,
        config: Optional[Dict] = None,
        session_id: Optional[str] = None,
        communication_style: str = "Analytical",
    ) -> None:
        """Initialize LLM-powered poker agent.

        Args:
            name: Agent's name
            chips: Starting chip count
            strategy_style: Initial strategy style
            personality_traits: Dict of personality trait values
            max_retries: Max LLM query retries
            retry_delay: Delay between retries
            use_reasoning: Whether to use chain-of-thought reasoning
            use_reflection: Whether to use self-reflection mechanism
            use_planning: Whether to use strategic planning
            use_opponent_modeling: Whether to use opponent modeling
            use_reward_learning: Whether to use reward-based learning
            learning_rate: Learning rate for reward-based learning
            config: Optional configuration dictionary
            session_id: Session ID for collection differentiation
            communication_style: Default communication style
        """
        super().__init__(name, chips)
        self.config = config
        self.use_reasoning = use_reasoning
        self.use_reflection = use_reflection
        self.use_planning = use_planning
        self.use_opponent_modeling = use_opponent_modeling
        self.use_reward_learning = use_reward_learning
        self.learning_rate = learning_rate

        self.last_message = ""
        self.last_opponent_action = None
        self.perception_history: List[Dict[str, Any]] = []
        self.conversation_history: List[Dict[str, Any]] = []
        self.strategy_style = strategy_style
        self.communication_style = communication_style
        self.emotional_state = "confident"
        self.table_history = []
        self.max_retries = 3
        self.retry_delay = 1.0
        self.personality_traits = {
            "aggression": 0.5,
            "bluff_frequency": 0.5,
            "risk_tolerance": 0.5,
        }

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = OpenAI(api_key=api_key)

        # Initialize LLM client
        from agents.llm_client import LLMClient

        self.llm_client = LLMClient(self.client)

        # Add plan tracking (only if planning is enabled)
        if self.use_planning:
            self.strategy_planner = StrategyPlanner(
                strategy_style=self.strategy_style,
                client=self.client,
                plan_duration=30.0,
            )

        # Initialize memory store with session-specific collection name
        collection_name = f"agent_{name.lower().replace(' ', '_')}_{session_id}_memory"
        self.memory_store = ChromaMemoryStore(collection_name)

        # Keep short-term memory in lists for immediate context
        self.short_term_limit = 3
        self.perception_history: List[Dict[str, Any]] = []
        self.conversation_history: List[Dict[str, Any]] = []

        # Initialize opponent modeling structures only if enabled
        if self.use_opponent_modeling:
            self.opponent_stats = defaultdict(
                lambda: {
                    "actions": defaultdict(int),
                    "bet_sizes": [],
                    "showdown_hands": [],
                    "bluff_attempts": 0,
                    "bluff_successes": 0,
                    "fold_to_raise_count": 0,
                    "raise_faced_count": 0,
                    "last_five_actions": [],
                    "position_stats": defaultdict(lambda: defaultdict(int)),
                }
            )
            self.opponent_models = {}

        # Initialize action history
        self.action_history = []

        # Initialize reward learning structures if enabled
        if self.use_reward_learning:
            self.action_history: List[Tuple[str, Dict[str, Any], int]] = (
                []
            )  # (action, state, reward)
            self.reward_weights = {
                "chip_gain": 1.0,
                "win_rate": 0.8,
                "bluff_success": 0.6,
                "position_value": 0.4,
            }
            self.action_values = {"fold": 0.0, "call": 0.0, "raise": 0.0}

        # Initialize strategy manager
        self.strategy_manager = StrategyManager(
            strategy_style or "Calculated and Cautious"
        )

        # Set active cognitive modules
        self.strategy_manager.active_modules.update(
            {
                "reasoning": use_reasoning,
                "reflection": use_reflection,
                "planning": use_planning,
            }
        )

    def close(self):
        """Clean up external resources explicitly.

        Ensures proper cleanup of:
        1. In-memory data structures (perception history, conversation history, plans)
        2. Memory store connection (ChromaDB)
        3. OpenAI client

        This method should be called explicitly when done with the agent, or used
        via the context manager pattern:

        Example:
            # Method 1: Explicit cleanup
            agent = LLMAgent(name="Bot1")
            try:
                # Use agent...
            finally:
                agent.close()

            # Method 2: Context manager (preferred)
            with LLMAgent(name="Bot2") as agent:
                # Use agent...
                # Cleanup happens automatically
        """
        try:
            # Clear in-memory data
            if hasattr(self, "perception_history"):
                self.perception_history.clear()
                del self.perception_history

            if hasattr(self, "conversation_history"):
                self.conversation_history.clear()
                del self.conversation_history

            if hasattr(self, "current_plan"):
                self.current_plan = None
                del self.current_plan

            if hasattr(self, "opponent_stats"):
                self.opponent_stats.clear()
                del self.opponent_stats

            if hasattr(self, "opponent_models"):
                self.opponent_models.clear()
                del self.opponent_models

            # Clean up memory store
            if hasattr(self, "memory_store"):
                try:
                    self.memory_store.close()
                except Exception as e:
                    if "Python is likely shutting down" not in str(e):
                        logging.warning(f"Error cleaning up memory store: {str(e)}")
                finally:
                    del self.memory_store

            # Clean up OpenAI client
            if hasattr(self, "client"):
                try:
                    del self.client
                except Exception as e:
                    if "Python is likely shutting down" not in str(e):
                        logging.warning(f"Error cleaning up OpenAI client: {str(e)}")

        except Exception as e:
            if "Python is likely shutting down" not in str(e):
                logging.error(f"Error in cleanup: {str(e)}")

    def __enter__(self):
        """Context manager entry point.

        Enables the agent to be used with Python's 'with' statement for automatic
        resource cleanup:

            with LLMAgent(name="Bot") as agent:
                # Agent is automatically cleaned up after this block

        Returns:
            LLMAgent: The agent instance
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point.

        Called automatically when exiting a 'with' block. Ensures cleanup happens
        even if an exception occurs within the block.

        Args:
            exc_type: Type of exception that occurred (if any)
            exc_val: Exception instance (if any)
            exc_tb: Exception traceback (if any)

        Note:
            Exceptions are not suppressed and will propagate after cleanup.
        """
        self.close()

    def __del__(self):
        """Fallback cleanup if close() wasn't called explicitly.

        This is a safety net for cases where the agent wasn't properly closed.
        However, it's better to use either:
        1. Explicit close() calls
        2. Context manager ('with' statement)

        Note:
            Errors are suppressed here since this may be called during interpreter
            shutdown when some resources are already gone.
        """
        try:
            self.close()
        except Exception:
            pass  # Suppress errors during interpreter shutdown

    def _get_decision_prompt(self, game_state: str) -> str:
        """Format the decision prompt with current game state and strategy."""
        # Get current plan if available
        current_plan = None
        if self.use_planning and hasattr(self, "strategy_planner"):
            current_plan = self.strategy_planner.current_plan

        # Format plan information if available
        plan_info = ""
        if current_plan:
            plan_info = f"""
Your current strategic plan:
- Approach: {current_plan.approach}
- Reasoning: {current_plan.reasoning}
- Bet Sizing: {current_plan.bet_sizing}
- Bluff Threshold: {current_plan.bluff_threshold}
- Fold Threshold: {current_plan.fold_threshold}
"""
        else:
            plan_info = "No active strategic plan."

        return DECISION_PROMPT.format(
            strategy_style=self.strategy_style,
            game_state=game_state,
            strategy_prompt=plan_info,
        )

    def decide_action(self, game_state: str) -> Tuple[str, int]:
        """Decide on an action for the current game state.

        Returns:
            Tuple[str, int]: A tuple containing:
                - action: 'fold', 'call', or 'raise'
                - amount: Amount to bet (for raises) or 0 (for fold/call)
        """
        try:
            # Get the decision prompt
            prompt = self._get_decision_prompt(game_state)

            # Get raw action from LLM
            raw_action = self.llm_client.decide_action(
                strategy_style=self.strategy_style,
                game_state=game_state,
                plan=self.current_plan.dict() if self.current_plan else {},
                min_raise=100,  # Default minimum raise
            )

            # Parse the action and amount
            if raw_action.startswith("raise"):
                action = "raise"
                try:
                    amount = int(raw_action.split()[1])
                except (IndexError, ValueError):
                    amount = 100  # Default raise amount
            elif raw_action == "fold":
                action = "fold"
                amount = 0
            else:  # Default to call
                action = "call"
                amount = 0

            return action, amount

        except Exception as e:
            self.logger.error(f"Decision error: {str(e)}")
            return "call", 0  # Safe default

    def _format_game_state(self, game_state: GameState) -> Dict[str, Any]:
        """Format game state into a dictionary representation."""
        try:
            # GameState now has a to_dict method that returns a structured dictionary
            return game_state.to_dict()
        except Exception as e:
            self.logger.error(f"Error formatting game state: {str(e)}")
            return {"error": "Failed to format game state", "raw": str(game_state)}

    def _extract_bet_amount(self, game_state: str) -> Optional[int]:
        """Extract current bet amount from game state."""
        try:
            return int(game_state.split("Current bet: $")[1].split(",")[0])
        except:
            return None

    def _extract_position(self, game_state: str) -> Optional[str]:
        """Extract player position from game state."""
        try:
            if "dealer" in game_state.lower():
                return "dealer"
            elif "small blind" in game_state.lower():
                return "small_blind"
            elif "big blind" in game_state.lower():
                return "big_blind"
            return None
        except:
            return None

    def get_message(self, game_state: str) -> str:
        """Generate table talk based on communication style and game state."""
        # Get recent table history
        table_history = (
            "\n".join(self.table_history[-3:])
            if self.table_history
            else "No recent history"
        )

        # First get strategic banter with intent
        banter_prompt = STRATEGIC_BANTER_PROMPT.format(
            strategy_style=self.strategy_style,
            game_state=game_state,
            position=self.position if hasattr(self, "position") else "unknown",
            recent_actions=self._format_recent_actions(),
            opponent_patterns=self._get_opponent_patterns(),
            communication_style=self.communication_style,
            emotional_state=self.emotional_state,
        )

        banter_response = self._query_llm(banter_prompt)

        # Parse the strategic response
        try:
            message_line = next(
                line
                for line in banter_response.split("\n")
                if line.startswith("MESSAGE:")
            )
            intent_line = next(
                line
                for line in banter_response.split("\n")
                if line.startswith("INTENT:")
            )
            confidence_line = next(
                line
                for line in banter_response.split("\n")
                if line.startswith("CONFIDENCE:")
            )

            # Store the intent and confidence for future reference
            self._last_message_intent = intent_line.replace("INTENT:", "").strip()
            self._last_message_confidence = int(
                confidence_line.replace("CONFIDENCE:", "").strip()
            )

            # Update emotional state based on confidence
            self._update_emotional_state(self._last_message_confidence)

            # Store in table history
            self.table_history.append(
                f"{self.name}: {message_line.replace('MESSAGE:', '').strip()}"
            )

            return message_line.replace("MESSAGE:", "").strip()

        except Exception as e:
            logger.error(f"Error parsing banter response: {e}")
            # Fallback to simple message prompt
            return self._get_simple_message(game_state, table_history)

    def _get_simple_message(self, game_state: str, table_history: str) -> str:
        """Fallback method for simple message generation."""
        prompt = MESSAGE_PROMPT.format(
            strategy_style=self.strategy_style,
            game_state=game_state,
            communication_style=self.communication_style,
            table_history=table_history,
        )
        message = self._query_llm(prompt)
        if message.startswith("MESSAGE:"):
            message = message.replace("MESSAGE:", "").strip()
        self.table_history.append(f"{self.name}: {message}")
        return message

    def _format_recent_actions(self) -> str:
        """Format recent game actions for context."""
        if not hasattr(self, "action_history"):
            return "No recent actions"
        return (
            "\n".join(self.action_history[-3:])
            if self.action_history
            else "No recent actions"
        )

    def _get_opponent_patterns(self) -> str:
        """Analyze and format opponent behavior patterns."""
        if not hasattr(self, "opponent_models"):
            return "No opponent data"
        patterns = []
        for opponent, model in self.opponent_models.items():
            if "style" in model:
                patterns.append(f"{opponent}: {model['style']}")
        return "\n".join(patterns) if patterns else "No clear patterns"

    def _update_emotional_state(self, confidence: int) -> None:
        """Update emotional state based on confidence and game situation."""
        if confidence >= 8:
            self.emotional_state = "confident"
        elif confidence <= 3:
            self.emotional_state = "nervous"
        elif 4 <= confidence <= 5:
            self.emotional_state = "thoughtful"
        elif 6 <= confidence <= 7:
            self.emotional_state = "amused"
        # Keep current state if no clear reason to change

    def perceive(self, game_state: str, opponent_message: Optional[str] = None) -> Dict:
        """Enhanced perception with communication context.

        Args:
            game_state (str): Current state of the game
            opponent_message (Optional[str]): Message from opponent, if any

        Returns:
            Dict: Enhanced perception data including memory updates
        """
        # Get base perception from parent class
        perception = super().perceive(game_state, opponent_message)

        # Add opponent message to table history if present
        if opponent_message:
            self.table_history.append(f"Opponent: {opponent_message}")
            # Trim history if too long
            if len(self.table_history) > 10:
                self.table_history = self.table_history[-10:]

        # Store perception in memory
        self.memory_store.add_memory(
            text=f"Game State: {game_state}"
            + (f"\nOpponent: {opponent_message}" if opponent_message else ""),
            metadata={"type": "perception", "timestamp": perception["timestamp"]},
        )

        return perception

    def decide_draw(self) -> List[int]:
        """Decide which cards to discard and draw new ones."""
        game_state = f"Hand: {self.hand.show()}"

        prompt = DISCARD_PROMPT.format(
            strategy_style=self.strategy_style,
            game_state=game_state,
            cards=[
                self.hand.cards[i] if i < len(self.hand.cards) else "N/A"
                for i in range(5)
            ],
        )

        try:
            response = self._query_llm(prompt)

            # First try to parse with strict format
            discard_positions = self._parse_discard(response)

            # If no DISCARD line found, try to extract from free text
            if not discard_positions and "discard" in response.lower():
                self.logger.warning(
                    f"No DISCARD: line found, attempting to parse from text: {response}"
                )

                # Look for numbers in text after "discard"
                import re

                numbers = re.findall(
                    r"\b[0-4]\b", response.lower().split("discard", 1)[1]
                )
                if numbers:
                    discard_positions = [
                        int(n) for n in numbers[:3]
                    ]  # Limit to 3 cards
                    self.logger.info(
                        f"Extracted positions from text: {discard_positions}"
                    )

            # Validate positions
            valid_positions = []
            for pos in discard_positions:
                if not isinstance(pos, int) or pos < 0 or pos > 4:
                    self.logger.warning(f"Invalid discard position {pos}")
                    continue
                valid_positions.append(pos)

            # Limit to 3 cards
            if len(valid_positions) > 3:
                self.logger.warning(
                    f"Too many discards ({len(valid_positions)}), limiting to 3"
                )
                valid_positions = valid_positions[:3]

            self.logger.info(f"{self.name} discarding positions: {valid_positions}")
            return valid_positions

        except Exception as e:
            self.logger.error(f"Error in decide_draw: {str(e)}")
            return []  # Safe fallback - keep all cards

    def _get_strategic_message(self, game_state: str) -> str:
        """Enhanced message generation with memory retrieval."""
        # Get relevant memories and format them
        query = f"Strategy: {self.strategy_style}, Game State: {game_state}"
        relevant_memories = self.memory_store.get_relevant_memories(query)
        memory_context = "\n".join(
            [f"Memory {i+1}: {mem['text']}" for i, mem in enumerate(relevant_memories)]
        )
        recent_conversation = "\n".join(
            [
                f"{msg['sender']}: {msg['message']}"
                for msg in self.conversation_history[-5:]
            ]
        )

        prompt = STRATEGIC_MESSAGE_PROMPT.format(
            strategy_style=self.strategy_style,
            game_state=game_state,
            recent_observations=(
                self.perception_history[-3:] if self.perception_history else "None"
            ),
            memory_context=memory_context,
            recent_conversation=recent_conversation,
        )

        message = self._query_llm(prompt).strip()

        # Store own message in memory
        self.conversation_history.append(
            {"sender": self.name, "message": message, "timestamp": time.time()}
        )
        self.memory_store.add_memory(
            text=message,
            metadata={
                "type": "conversation",
                "sender": self.name,
                "timestamp": time.time(),
                "strategy_style": self.strategy_style,
            },
        )

        self.last_message = message
        return message

    def interpret_message(self, opponent_message: str) -> str:
        """Analyze and interpret opponent's message using historical context.

        Evaluates opponent messages by considering recent game history, conversation patterns,
        and the agent's strategic style to determine appropriate response strategy.

        Args:
            opponent_message (str): Message received from the opponent

        Returns:
            str: Interpretation result, one of:
                - 'trust': Message appears genuine
                - 'ignore': Message is irrelevant or misleading
                - 'counter-bluff': Message indicates opponent bluffing

        Note:
            Uses LLM to analyze message sentiment and intent based on game context.
        """
        recent_history = self.perception_history[-3:] if self.perception_history else []

        prompt = INTERPRET_MESSAGE_PROMPT.format(
            strategy_style=self.strategy_style,
            opponent_message=opponent_message,
            recent_history=recent_history,
        )
        return self._query_llm(prompt).strip().lower()

    def _normalize_action(self, action: str) -> str:
        """Normalize the LLM's action response to a valid poker action.

        Args:
            action (str): Raw action string from LLM (e.g. 'check', 'bet', or sentence)

        Returns:
            str: Normalized action ('fold', 'call', or 'raise')

        Examples:
            >>> agent._normalize_action("I want to check")
            'call'
            >>> agent._normalize_action("bet 100")
            'raise'
            >>> agent._normalize_action("FOLD!")
            'fold'
        """
        # Remove any quotes and extra whitespace
        action = action.lower().strip().strip("'\"")

        # Extract just the action word if it's embedded in a sentence
        action_words = {
            "fold": "fold",
            "call": "call",
            "raise": "raise",
            "check": "call",  # normalize check to call
            "bet": "raise",  # normalize bet to raise
        }

        # First try exact match
        if action in action_words:
            return action_words[action]

        # Then look for action words in the response
        for word in action.split():
            word = word.strip(".:,!?*()[]'\"")  # Remove punctuation and quotes
            if word in action_words:
                return action_words[word]

        # If no valid action found, log and return None
        self.logger.warning("Could not parse action from LLM response: '%s'", action)
        return None

    def get_action(
        self, game_state: str, opponent_message: Optional[str] = None
    ) -> str:
        """Determine the next action based on the game state and opponent's message."""
        try:
            prompt = EXECUTION_PROMPT.format(
                strategy_style=self.strategy_style,
                game_state=game_state,
                plan_approach=self.current_plan["approach"],
                plan_reasoning=self.current_plan["reasoning"],
                bluff_threshold=self.current_plan["bluff_threshold"],
                fold_threshold=self.current_plan["fold_threshold"],
            )

            response = self._query_llm(prompt)

            # Parse with strict format checking
            action = self._parse_decision(response)

            # Validate action
            if action not in ["fold", "call", "raise"]:
                self.logger.warning(f"Invalid action {action}, defaulting to call")
                return "call"

            self.logger.info(f"{self.name} decided to {action}")
            return action

        except Exception as e:
            self.logger.error(f"Error in get_action: {str(e)}")
            return "call"  # Safe fallback

    async def _query_gpt_async(self, prompt: str) -> str:
        """Asynchronous query to OpenAI's GPT model with error handling and timeout.

        Makes an asynchronous request to GPT with proper context management and
        timeout handling.

        Args:
            prompt (str): The prompt to send to GPT

        Returns:
            str: Response from GPT model

        Raises:
            OpenAIError: If query fails or times out
            asyncio.TimeoutError: If query exceeds 10 second timeout

        Note:
            - Sets system message based on agent's traits and enabled features
            - Includes recent conversation history for context
            - Uses GPT-3.5-turbo model with standardized parameters
            - Implements 10 second timeout for queries
        """
        try:
            # Adjust system message based on enabled features
            system_content = f"""You are a {self.strategy_style} poker player with these traits:
                - Aggression: {self.personality_traits['aggression']:.1f}/1.0
                - Bluff_Frequency: {self.personality_traits['bluff_frequency']:.1f}/1.0
                - Risk_Tolerance: {self.personality_traits['risk_tolerance']:.1f}/1.0
                
                {
                    "Think through your decisions step by step, but stay in character "
                    "and be consistent with these traits. Your reasoning should reflect "
                    "your personality." if self.use_reasoning else 
                    "Stay in character and be consistent with these traits."
                }"""

            messages = [{"role": "system", "content": system_content}]

            if self.conversation_history:
                for entry in self.conversation_history[-4:]:
                    role = "assistant" if entry["sender"] == self.name else "user"
                    messages.append({"role": role, "content": entry["message"]})

            messages.append({"role": "user", "content": prompt})

            async with asyncio.timeout(10):  # 10 second timeout
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model="gpt-3.5-turbo",  # Standardized to 3.5-turbo
                        messages=messages,
                        max_tokens=150,
                        temperature=0.7,
                    ),
                )

            if not response.choices:
                raise OpenAIError("Empty response from GPT")

            return response.choices[0].message.content

        except asyncio.TimeoutError:
            self.logger.error("GPT query timed out after 10 seconds")
            raise OpenAIError("Query timed out")
        except Exception as e:
            self.logger.error(f"GPT query failed: {str(e)}")
            raise OpenAIError(str(e))

    def _query_gpt(self, prompt: str) -> str:
        """Synchronous wrapper for async GPT query."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(self._query_gpt_async(prompt))
        except Exception as e:
            self.logger.error(f"GPT query failed: {str(e)}")
            # Return fallback response
            if "get_action" in prompt.lower():
                return "call"
            return "I need to think about my next move."

    def _query_llm(self, prompt: str, max_retries: int = 3) -> str:
        """Query LLM with retry logic and better error handling.

        Args:
            prompt: Formatted prompt string
            max_retries: Maximum number of retry attempts

        Returns:
            str: LLM response text

        Raises:
            LLMError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=150,  # Limit response length
                )
                return response.choices[0].message.content

            except Exception as e:
                self.logger.warning(f"LLM query attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise LLMError(
                        f"All {max_retries} LLM query attempts failed"
                    ) from e
                time.sleep(1)  # Wait before retry

    def update_strategy(self, game_outcome: Dict[str, Any]) -> None:
        """Update agent's strategy based on game outcomes and performance.

        Analyzes game results to potentially adjust strategy style and decision-making
        patterns for future games. Uses LLM to evaluate strategy effectiveness.

        Args:
            game_outcome (dict): Results and statistics from the completed game

        Note:
            - Can switch between predefined strategy styles
            - Considers recent history in decision
            - Logs strategy changes for monitoring
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
            self.logger.info(
                "[Strategy Update] %s changing strategy from %s to %s",
                self.name,
                self.strategy_style,
                strategy_map[response],
            )
            self.strategy_style = strategy_map[response]

    def analyze_opponent(self, opponent_name: str, game_state: str) -> Dict[str, Any]:
        """Enhanced opponent analysis using historical data and LLM interpretation.

        Analyzes opponent patterns considering:
        - Action frequencies
        - Betting patterns
        - Position-based tendencies
        - Bluffing frequency
        - Response to aggression
        """
        # Default analysis structure
        default_analysis = {
            "patterns": "unknown",
            "threat_level": "medium",
            "style": "unknown",
            "weaknesses": [],
            "strengths": [],
            "recommended_adjustments": [],
        }

        # Return default if opponent modeling is disabled
        if not self.use_opponent_modeling:
            return default_analysis

        stats = self.opponent_stats[opponent_name]

        # Return default if insufficient data
        total_actions = sum(stats["actions"].values())
        if total_actions == 0:
            default_analysis.update(
                {
                    "patterns": "insufficient data",
                    "style": "unknown",
                    "threat_level": "unknown",
                }
            )
            return default_analysis

        # Calculate key metrics
        aggression_frequency = (
            (stats["actions"]["raise"] / total_actions) if total_actions > 0 else 0
        )
        fold_to_raise_ratio = (
            (stats["fold_to_raise_count"] / stats["raise_faced_count"])
            if stats["raise_faced_count"] > 0
            else 0
        )
        bluff_success_rate = (
            (stats["bluff_successes"] / stats["bluff_attempts"])
            if stats["bluff_attempts"] > 0
            else 0
        )

        # Prepare statistical summary for LLM
        stats_summary = f"""
        Opponent Analysis for {opponent_name}:
        - Action Distribution: {dict(stats['actions'])}
        - Average Bet Size: ${np.mean(stats['bet_sizes']) if stats['bet_sizes'] else 0:.2f}
        - Fold to Raise: {fold_to_raise_ratio:.2%}
        - Bluff Success Rate: {bluff_success_rate:.2%}
        - Recent Actions: {stats['last_five_actions'][-5:]}
        - Position Tendencies: {dict(stats['position_stats'])}
        """

        prompt = f"""
        Analyze this poker opponent's playing style and patterns:
        
        {stats_summary}
        Current Game State: {game_state}
        
        Provide a detailed analysis in this exact JSON format:
        {{
            "patterns": "<primary pattern>",
            "threat_level": "<low/medium/high>",
            "style": "<tight-aggressive/loose-passive/unknown>",
            "weaknesses": ["<exploitable pattern>"],
            "strengths": ["<strong pattern>"],
            "recommended_adjustments": ["<strategic adjustment>"]
        }}
        
        Base the analysis on:
        1. Position-based tendencies
        2. Betting patterns and sizes
        3. Response to aggression
        4. Bluffing frequency and success
        5. Recent behavior changes
        
        Always include all fields, use "unknown" for uncertain values.
        """

        try:
            response = self._query_llm(prompt)
            analysis = eval(response.strip())  # Safe since we control LLM output format

            # Ensure all required keys are present
            for key in default_analysis:
                if key not in analysis:
                    analysis[key] = default_analysis[key]

            # Cache analysis for future reference
            self.opponent_models[opponent_name] = {
                "last_analysis": analysis,
                "timestamp": time.time(),
                "confidence": min(
                    total_actions / 20, 1.0
                ),  # Confidence based on sample size
            }

            return analysis

        except Exception as e:
            self.logger.error(f"Error in opponent analysis: {str(e)}")
            return default_analysis

    def update_opponent_stats(
        self,
        opponent_name: str,
        action: str,
        amount: Optional[int] = None,
        position: Optional[str] = None,
        hand_shown: Optional[str] = None,
        was_bluff: Optional[bool] = None,
    ) -> None:
        """Update opponent statistics with new action data."""
        stats = self.opponent_stats[opponent_name]

        # Update action counts
        stats["actions"][action] += 1

        # Track betting amounts
        if amount is not None and action in ["raise", "call"]:
            stats["bet_sizes"].append(amount)

        # Update position-based stats
        if position:
            stats["position_stats"][position][action] += 1

        # Track recent actions
        stats["last_five_actions"].append((action, amount))
        if len(stats["last_five_actions"]) > 5:
            stats["last_five_actions"].pop(0)

        # Update bluff tracking
        if was_bluff is not None:
            stats["bluff_attempts"] += 1
            if was_bluff:
                stats["bluff_successes"] += 1

        # Update fold to raise stats
        if action == "fold" and getattr(self, "last_opponent_action", None) == "raise":
            stats["fold_to_raise_count"] += 1
        if action == "raise":
            stats["raise_faced_count"] += 1

        # Store shown hands
        if hand_shown:
            stats["showdown_hands"].append(hand_shown)

    def reset_state(self) -> None:
        """Reset agent's state and clear memory store."""
        self.perception_history = []
        self.conversation_history = []
        self.last_message = ""
        self.memory_store.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Retrieve current agent statistics and state information.

        Collects various metrics and state information about the agent's
        current configuration and performance.

        Returns:
            dict: Statistics including:
                - name: Agent identifier
                - strategy_style: Current strategy approach
                - perception_history_length: Number of stored perceptions
                - model_type: Type of LLM being used
                - last_message: Most recent message sent
                - features: Dict of enabled/disabled features
                - current_plan: Active strategy plan (if planning enabled)
        """
        stats = {
            "name": self.name,
            "strategy_style": self.strategy_style,
            "perception_history_length": len(self.perception_history),
            "model_type": self.model_type,
            "last_message": self.last_message,
            "features": {
                "planning": self.use_planning,
                "reasoning": self.use_reasoning,
                "reflection": self.use_reflection,
            },
        }
        if self.use_planning and self.current_plan:
            stats["current_plan"] = {
                "approach": self.current_plan.approach,
                "expires_in": max(0, self.plan_expiry - time.time()),
            }
        return stats

    def plan_strategy(self, game_state: str) -> Plan:
        """Generate or update the agent's strategic plan.

        Creates a short-term strategic plan considering the agent's traits, current
        game state, and recent history. Plans include approach, bet sizing, and
        thresholds for actions.

        Args:
            game_state: Current state of the game

        Returns:
            Plan: Strategic plan containing approach, bet sizing, thresholds, etc.
        """
        # Check if we have a valid current plan
        current_time = time.time()
        if (
            self.current_plan
            and current_time < self.plan_expiry
            and not self._should_replan(game_state)
        ):
            return self.current_plan

        # Create planning prompt with escaped curly braces for the JSON template
        planning_prompt = PLANNING_PROMPT.format(
            strategy_style=self.strategy_style, game_state=game_state
        )

        try:
            response = self._query_llm(planning_prompt)
            plan_data = eval(
                response.strip()
            )  # Safe since we control LLM output format

            # Create Plan instance with proper expiry time
            plan = Plan(
                approach=Approach(plan_data.get("approach", "balanced")),
                reasoning=plan_data.get(
                    "reasoning", "Error in planning, using balanced approach"
                ),
                bet_sizing=BetSizing(plan_data.get("bet_sizing", "medium")),
                bluff_threshold=float(plan_data.get("bluff_threshold", 0.7)),
                fold_threshold=float(plan_data.get("fold_threshold", 0.3)),
                expiry=current_time + 300,  # 5 minute expiry
                adjustments=[],
                target_opponent=None,
            )

            # Update plan tracking
            self.current_plan = plan
            self.plan_expiry = plan.expiry

            self.logger.info(
                f"[Planning] {self.name} adopted {plan.approach} approach: {plan.reasoning}"
            )
            return plan

        except Exception as e:
            self.logger.error(f"Planning failed: {str(e)}")
            # Return fallback Plan object instead of dictionary
            return Plan(
                approach=Approach.BALANCED,
                reasoning="Error in planning, falling back to balanced approach",
                bet_sizing=BetSizing.MEDIUM,
                bluff_threshold=0.7,
                fold_threshold=0.3,
                expiry=current_time + 300,  # 5 minute expiry
                adjustments=[],
                target_opponent=None,
            )

    def _should_replan(self, game_state: str) -> bool:
        """Determine if current plan should be abandoned for a new one.

        Evaluates game state changes to decide if current strategic plan
        remains valid or needs updating.

        Args:
            game_state (str): Current state of the game

        Returns:
            bool: True if replanning needed, False otherwise

        Note:
            Triggers replanning on:
            - Significant bet sizes (>30% of chips)
            - Low chip stack (<300)
            - Missing current plan
        """
        if not self.current_plan:
            return True

        # Extract key metrics from game state
        try:
            current_bet = int(game_state.split("Current bet: $")[1].split(",")[0])
            chips = int(game_state.split("Your chips: $")[1].split(",")[0])

            # Replan if significant changes occurred
            significant_bet = current_bet > chips * 0.3
            low_stack = chips < 300  # Arbitrary threshold

            return significant_bet or low_stack

        except:
            return False

    def execute_action(self, plan: Dict[str, Any], game_state: str) -> str:
        """Execute specific action based on current plan and game state.

        Translates strategic plan into concrete poker action considering
        current situation and plan parameters.

        Args:
            plan (dict): Current strategic plan
            game_state (str): Current game state

        Returns:
            str: Concrete action ('fold', 'call', or 'raise')

        Note:
            - Falls back to 'call' if execution fails
            - Considers bluff and fold thresholds from plan
            - Evaluates pot odds and immediate costs
        """
        execution_prompt = EXECUTION_PROMPT.format(
            strategy_style=self.strategy_style,
            game_state=game_state,
            plan_approach=self.current_plan["approach"],
            plan_reasoning=self.current_plan["reasoning"],
            bluff_threshold=self.current_plan["bluff_threshold"],
            fold_threshold=self.current_plan["fold_threshold"],
        )

        try:
            response = self._query_llm(execution_prompt)
            if "EXECUTE:" not in response:
                raise ValueError("No EXECUTE directive found")

            action = response.split("EXECUTE:")[1].strip().split()[0]
            return self._normalize_action(action)

        except Exception as e:
            self.logger.error(f"Execution failed: {str(e)}")
            return "call"  # Safe fallback

    def update_from_reward(self, reward: int, game_state: Dict[str, Any]) -> None:
        """Update agent's strategy based on rewards received using temporal difference learning.

        Implements a reward-based learning system that:
        1. Records action-reward pairs in action history
        2. Updates action values using TD learning
        3. Adjusts personality traits based on outcomes

        Args:
            reward (int): Numerical reward value (positive for wins, negative for losses)
            game_state (Dict[str, Any]): Current game state containing:
                - all_in (bool): Whether the hand involved an all-in
                - bluff_successful (bool): Whether a bluff attempt succeeded
                - bluff_caught (bool): Whether a bluff was caught
                - Other game state information

        Note:
            - Only processes updates if reward learning is enabled
            - Uses learning rate to control adaptation speed
            - Maintains action values for fold/call/raise
        """
        if not self.use_reward_learning:
            return

        # Record action and reward
        if hasattr(self, "last_action"):
            self.action_history.append((self.last_action, game_state, reward))

        # Update action values using temporal difference learning
        if len(self.action_history) > 1:
            prev_action, prev_state, prev_reward = self.action_history[-2]
            current_value = self.action_values[prev_action]
            # TD update
            self.action_values[prev_action] = current_value + self.learning_rate * (
                reward + 0.9 * max(self.action_values.values()) - current_value
            )

        # Adjust personality traits based on rewards
        if reward > 0:
            self._adjust_traits_from_success(game_state)
        else:
            self._adjust_traits_from_failure(game_state)

    def _adjust_traits_from_success(self, game_state: Dict[str, Any]) -> None:
        """Incrementally adjust personality traits after successful outcomes.

        Reinforces successful strategies by increasing relevant trait values:
        - Increases risk tolerance after successful all-in plays
        - Increases bluff frequency after successful bluffs

        Args:
            game_state (Dict[str, Any]): Game state containing:
                - all_in (bool): Whether hand was all-in
                - bluff_successful (bool): Whether bluff succeeded

        Note:
            - Adjustments are capped at 1.0 (maximum trait value)
            - Uses fixed 0.05 increment for trait adjustments
        """
        # Small adjustments to traits that led to success
        if "all_in" in game_state and game_state["all_in"]:
            self.personality_traits["risk_tolerance"] = min(
                1.0, self.personality_traits["risk_tolerance"] + 0.05
            )
        if "bluff_successful" in game_state and game_state["bluff_successful"]:
            self.personality_traits["bluff_frequency"] = min(
                1.0, self.personality_traits["bluff_frequency"] + 0.05
            )

    def _adjust_traits_from_failure(self, game_state: Dict[str, Any]) -> None:
        """Incrementally adjust personality traits after failed outcomes.

        Reduces trait values associated with failed strategies:
        - Decreases risk tolerance after losing all-in plays
        - Decreases bluff frequency after caught bluffs

        Args:
            game_state (Dict[str, Any]): Game state containing:
                - all_in (bool): Whether hand was all-in
                - bluff_caught (bool): Whether bluff was caught

        Note:
            - Adjustments are bounded at 0.0 (minimum trait value)
            - Uses fixed 0.05 decrement for trait adjustments
        """
        # Small adjustments to traits that led to failure
        if "all_in" in game_state and game_state["all_in"]:
            self.personality_traits["risk_tolerance"] = max(
                0.0, self.personality_traits["risk_tolerance"] - 0.05
            )
        if "bluff_caught" in game_state and game_state["bluff_caught"]:
            self.personality_traits["bluff_frequency"] = max(
                0.0, self.personality_traits["bluff_frequency"] - 0.05
            )

    def _get_action_probabilities(self) -> Dict[str, float]:
        """Convert action values to probability distribution using softmax normalization.

        Transforms raw action values into probabilities for action selection:
        1. Applies exponential to values (with numerical stability adjustment)
        2. Normalizes to create valid probability distribution

        Returns:
            Dict[str, float]: Mapping of actions to their probabilities:
                - 'fold': probability of folding
                - 'call': probability of calling
                - 'raise': probability of raising

        Note:
            Uses numpy's exp for efficient computation and numerical stability
        """
        values = np.array(list(self.action_values.values()))
        exp_values = np.exp(
            values - np.max(values)
        )  # Subtract max for numerical stability
        probabilities = exp_values / np.sum(exp_values)
        return dict(zip(self.action_values.keys(), probabilities))

    def _is_bubble_situation(self, game_state: str) -> bool:
        """Determine if the current game state represents a tournament bubble situation.

        A bubble situation typically occurs when:
        1. We're in a tournament (vs cash game)
        2. Players are close to making the money
        3. Stack sizes become critical for survival

        Args:
            game_state (str): Current game state description

        Returns:
            bool: True if we're in a bubble situation, False otherwise
        """
        try:
            # Look for bubble indicators in game state
            is_bubble = "tournament" in game_state.lower() and (
                "bubble" in game_state.lower()
                or "near money" in game_state.lower()
                or "money bubble" in game_state.lower()
            )

            # Also check for critical stack size situations
            if not is_bubble:
                try:
                    # Extract number of players if available
                    players_left = int(
                        game_state.split("players remaining:")[1].split()[0]
                    )
                    # Typical bubble situations are near prize positions
                    if players_left <= 10:  # Arbitrary threshold
                        return True
                except:
                    pass

            return is_bubble

        except Exception as e:
            self.logger.warning(f"Error checking bubble situation: {str(e)}")
            return False

    def _parse_decision(self, response: str) -> str:
        """Parse the decision from LLM response with strict format checking.

        Extracts and validates the action from a response containing a 'DECISION:' line.

        Args:
            response (str): Full LLM response text

        Returns:
            str: Validated action ('fold', 'call', or 'raise'). Defaults to 'call' if parsing fails.

        Example:
            >>> response = "Analysis: Good hand\nDECISION: raise\nReasoning: Strong cards"
            >>> agent._parse_decision(response)
            'raise'
        """
        try:
            # Look for DECISION: line
            decision_line = [
                line for line in response.split("\n") if line.startswith("DECISION:")
            ]
            if not decision_line:
                logger.warning("No DECISION: line found in response")
                return "call"  # safe default

            # Extract action
            action = decision_line[0].split("DECISION:")[1].strip().lower()

            # Validate action
            if action not in ["fold", "call", "raise"]:
                logger.warning(f"Invalid action '{action}' found in response")
                return "call"

            return action

        except Exception as e:
            logger.error(f"Error parsing decision: {e}")
            return "call"

    def _parse_discard(self, response: str) -> List[int]:
        """Parse the discard positions from LLM response with strict format checking.

        Extracts and validates card positions to discard from a response containing a 'DISCARD:' line.

        Args:
            response (str): Full LLM response text

        Returns:
            List[int]: List of valid card positions (0-4) to discard, limited to 3 cards.
                      Returns empty list if parsing fails.

        Example:
            >>> response = "Analysis: Weak cards\nDISCARD: [0, 2, 4]\nReasoning: Poor cards"
            >>> agent._parse_discard(response)
            [0, 2, 4]
        """
        try:
            # Look for DISCARD: line
            discard_line = [
                line for line in response.split("\n") if line.startswith("DISCARD:")
            ]
            if not discard_line:
                logger.warning("No DISCARD: line found in response")
                return []

            # Extract positions
            positions_str = discard_line[0].split("DISCARD:")[1].strip()
            if positions_str.lower() == "none":
                return []

            # Parse list of positions
            positions = eval(positions_str)  # safely evaluate [0,2,4] format

            # Validate positions
            if not all(isinstance(p, int) and 0 <= p <= 4 for p in positions):
                logger.warning(f"Invalid positions {positions} found in response")
                return []

            # Sort positions and limit to 3 cards
            return sorted(positions)[:3]  # Add this line to limit to 3 cards

        except Exception as e:
            logger.error(f"Error parsing discard positions: {e}")
            return []

    def _get_basic_action(self, game_state: str) -> str:
        """Make a basic decision without complex planning."""
        try:
            # Get relevant memories for context, handle case with few memories
            try:
                memories = self.memory_store.get_relevant_memories(game_state, k=2)
            except Exception as e:
                self.logger.debug(f"Memory retrieval adjusted: {str(e)}")
                # Try with k=1 if k=2 fails, or empty list as fallback
                try:
                    memories = self.memory_store.get_relevant_memories(game_state, k=1)
                except:
                    memories = []

            # Format prompt with game state and memories
            prompt = self._format_decision_prompt(game_state, memories)

            # Query LLM for decision
            response = self._query_llm(prompt)

            # Parse and validate response
            action = self._parse_action(response)

            # Store decision in memory
            self._store_decision_memory(game_state, action)

            return action

        except Exception as e:
            self.logger.error(f"Basic decision error: {str(e)}")
            return "fold"  # Safe default

    def _get_strategic_action(self, game_state: str) -> str:
        """Get action using strategic planning."""
        try:
            # Get or create strategic plan
            plan = self.strategy_planner.plan_strategy(game_state, self.chips)

            # Execute plan to get concrete action
            action = self.strategy_planner.execute_action(game_state)

            self.logger.info(
                f"[{self.name}] Strategy plan: {plan['approach']} -> Action: {action}"
            )
            return action

        except Exception as e:
            self.logger.error(f"Strategic action error: {str(e)}")
            return "call"  # Safe default

    def _format_decision_prompt(
        self, game_state: str, memories: List[Dict[str, Any]]
    ) -> str:
        """Format prompt for basic decision making."""
        # Format memories for context
        memory_context = ""
        if memories:
            memory_context = "\nRecent relevant experiences:\n" + "\n".join(
                [f"- {mem['text']}" for mem in memories]
            )

        # Get opponent patterns if modeling is enabled
        opponent_context = ""
        if self.use_opponent_modeling and hasattr(self, "opponent_models"):
            patterns = []
            for opp, model in self.opponent_models.items():
                if "style" in model:
                    patterns.append(f"{opp}: {model['style']}")
            if patterns:
                opponent_context = "\nOpponent patterns:\n" + "\n".join(patterns)

        return f"""You are a {self.strategy_style} poker player.
Current game state:
{game_state}
{memory_context}
{opponent_context}

Decide your action (fold/call/raise) based on:
1. Your strategy style ({self.strategy_style})
2. Current game state
3. Historical context
4. Opponent patterns

Respond with DECISION: followed by your action.
Example: "DECISION: call"
"""

    def _store_decision_memory(self, game_state: str, action: str) -> None:
        """Store decision in memory for future reference."""
        self.memory_store.add_memory(
            text=f"Made decision to {action} in state: {game_state}",
            metadata={
                "type": "decision",
                "action": action,
                "timestamp": time.time(),
                "strategy_style": self.strategy_style,
            },
        )

    def _parse_action(self, response: str) -> str:
        """Parse and validate action from LLM response.

        Args:
            response: Raw response string from LLM

        Returns:
            str: Normalized action ('fold', 'call', or 'raise')
        """
        try:
            # Look for DECISION: line with more flexible parsing
            if "DECISION:" not in response:
                self.logger.warning(
                    f"No DECISION: found in response: {response[:100]}..."
                )
                return "call"

            # Extract everything after DECISION: and before next newline
            decision_line = [
                line for line in response.split("\n") if "DECISION:" in line
            ][0]
            action = decision_line.split("DECISION:")[1].strip().split()[0].lower()

            # Validate action
            valid_actions = ["fold", "call", "raise"]
            if action not in valid_actions:
                self.logger.warning(
                    f"Invalid action '{action}' in response: {response[:100]}..."
                )
                return "call"

            return action

        except Exception as e:
            self.logger.error(
                f"Error parsing action: {str(e)}\nResponse: {response[:100]}..."
            )
            return "call"  # Safe default

    def get_relevant_memories(self, query: str) -> List[Dict[str, Any]]:
        """Get relevant memories for decision making.

        Args:
            query: Query string to search memories

        Returns:
            List[Dict[str, Any]]: List of relevant memories, may be empty
        """
        try:
            # First check how many memories we have available
            all_memories = self.memory_store.get_relevant_memories(query, k=1)

            # If we have memories, try getting more
            if all_memories:
                try:
                    # Try getting 2 memories, but will get 1 if that's all that exists
                    memories = self.memory_store.get_relevant_memories(query, k=2)
                    return memories
                except Exception:
                    # Fall back to the single memory we know exists
                    return all_memories

            return []  # No memories found

        except Exception as e:
            self.logger.debug(f"Memory retrieval failed: {str(e)}")
            return []  # Return empty list on error

    def _create_memory_query(self, game_state: Dict[str, Any]) -> str:
        """Create a query string from game state for memory retrieval.

        Args:
            game_state: Dictionary containing current game state

        Returns:
            str: Formatted query string for memory retrieval
        """
        try:
            # Extract key information from game state
            current_bet = game_state.get("current_bet", 0)
            pot = game_state.get("pot", 0)

            # Get player information
            players_info = []
            for p in game_state.get("players", []):
                players_info.append(
                    f"{p['name']}(${p['chips']}, bet:${p.get('bet', 0)})"
                )

            # Create query combining key game state elements
            query = (
                f"Game situation with pot ${pot}, current bet ${current_bet}, "
                f"players: {', '.join(players_info)}"
            )

            # Add position context if available
            if "position" in game_state:
                query += f", position: {game_state['position']}"

            return query

        except Exception as e:
            self.logger.error(f"Error creating memory query: {str(e)}")
            return str(game_state)  # Fallback to basic string conversion
