import asyncio
import logging
import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from dotenv import load_dotenv

from agents.base_agent import BaseAgent
from agents.llm_client import LLMClient
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
from exceptions import OpenAIError
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

        # Initialize LLM client first
        self.llm_client = LLMClient(
            api_key=os.getenv("OPENAI_API_KEY"), model="gpt-3.5-turbo"
        )

        # Then initialize strategy planner with llm_client
        if self.use_planning:
            self.strategy_planner = StrategyPlanner(
                strategy_style=self.strategy_style,
                client=self.llm_client,  # Pass llm_client instead of self.client
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

    def decide_action(self, game_state: Union[str, Dict[str, Any]]) -> Tuple[str, int]:
        """Decide poker action using LLM."""
        try:
            # Create decision prompt
            prompt = self._create_decision_prompt(game_state)

            # Add system message for strategy context
            system_message = (
                f"You are a {self.strategy_style} poker player making decisions."
            )

            # Query LLM with retry logic
            response = self._query_llm(
                prompt=prompt, temperature=0.7, system_message=system_message
            ).strip()  # Strip whitespace from full response

            # Debug logging
            self.logger.debug(f"Raw LLM response:\n{response}")

            # Parse and validate response
            # Look for DECISION: line
            if "DECISION:" not in response:
                self.logger.warning(
                    f"No DECISION: found in response: {response[:100]}..."
                )
                return "fold", 0

            try:
                # Extract decision line, handling potential whitespace
                decision_line = next(
                    line.strip() for line in response.split("\n") if "DECISION:" in line
                )

                # Debug logging
                self.logger.debug(f"Found decision line: {decision_line}")

                # Parse action and amount
                parts = decision_line.replace("DECISION:", "").strip().split()
                action = parts[0].lower()

                # Debug logging
                self.logger.debug(f"Parsed action: {action}, parts: {parts}")

                # Validate action
                if action not in ["fold", "call", "raise"]:
                    self.logger.warning(f"Invalid action '{action}' in response")
                    return "fold", 0

                # Extract amount for raise
                amount = 0
                if action == "raise" and len(parts) > 1:
                    try:
                        amount = int(parts[1])
                        self.logger.debug(f"Parsed raise amount: {amount}")
                    except (IndexError, ValueError) as e:
                        self.logger.warning(f"Error parsing raise amount: {e}")
                        amount = 100  # Default raise amount

                # Validate final amount
                amount = self._validate_bet_amount(f"{action} {amount}")

                # Debug logging
                self.logger.debug(f"Final decision: {action} {amount}")

                return action, amount

            except StopIteration:
                self.logger.warning("Could not find valid DECISION line in response")
                return "fold", 0

        except Exception as e:
            self.logger.error(f"Error in decide_action: {str(e)}")
            return "fold", 0  # Safe default

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

    def get_message(self, game_state: Union[str, Dict[str, Any]]) -> str:
        """Generate table talk using LLM."""
        try:
            # Create message prompt
            prompt = self._create_message_prompt(game_state)

            system_message = (
                f"You are a {self.communication_style} {self.strategy_style} "
                f"poker player engaging in table talk."
            )

            # Query LLM with lower temperature for more consistent messaging
            response = self._query_llm(
                prompt=prompt, temperature=0.5, system_message=system_message
            )

            return self._parse_message(response)

        except Exception as e:
            self.logger.error(f"Error generating message: {str(e)}")
            return ""  # Safe default

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

    def decide_draw(self, game_state: Optional[Dict[str, Any]] = None) -> List[int]:
        """Decide which cards to discard."""
        try:
            # Create draw decision prompt
            prompt = DISCARD_PROMPT.format(
                strategy_style=self.strategy_style,
                hand=self.hand.show() if hasattr(self, "hand") else "No hand",
                game_state=game_state or "No game state",
            )

            system_message = (
                f"You are a {self.strategy_style} poker player deciding which "
                f"cards to discard in draw poker."
            )

            # Query LLM for discard decision
            response = self._query_llm(
                prompt=prompt, temperature=0.7, system_message=system_message
            )

            # Parse response for discard positions
            if "DISCARD:" not in response:
                return []

            discard_line = next(
                line for line in response.split("\n") if line.startswith("DISCARD:")
            )

            # Parse positions, ensuring they're valid (0-4)
            try:
                positions = [
                    int(pos)
                    for pos in discard_line.replace("DISCARD:", "").strip().split()
                    if 0 <= int(pos) <= 4
                ]
                return positions[:3]  # Maximum 3 discards
            except ValueError:
                return []

        except Exception as e:
            self.logger.error(f"Error in decide_draw: {str(e)}")
            return []

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

    def interpret_message(self, message: str) -> str:
        """Interpret opponent's message."""
        try:
            prompt = INTERPRET_MESSAGE_PROMPT.format(
                strategy_style=self.strategy_style,
                message=message,
                recent_history=(
                    self.table_history[-3:] if self.table_history else "No history"
                ),
                opponent_patterns=self._get_opponent_patterns(),
            )

            system_message = (
                f"You are a {self.strategy_style} poker player analyzing "
                f"an opponent's table talk."
            )

            response = self._query_llm(
                prompt=prompt, temperature=0.5, system_message=system_message
            )

            # Parse interpretation (trust/ignore/counter-bluff)
            if "INTERPRETATION:" in response:
                interp_line = next(
                    line
                    for line in response.split("\n")
                    if line.startswith("INTERPRETATION:")
                )
                interpretation = (
                    interp_line.replace("INTERPRETATION:", "").strip().lower()
                )

                valid_interpretations = ["trust", "ignore", "counter-bluff"]
                if interpretation in valid_interpretations:
                    return interpretation

            return "ignore"  # Default to ignoring if parsing fails

        except Exception as e:
            self.logger.error(f"Error interpreting message: {str(e)}")
            return "ignore"

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

    def _query_llm(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
        system_message: Optional[str] = None,
    ) -> str:
        """Query LLM with retry logic and error handling."""
        try:
            return self.llm_client.query(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                system_message=system_message,
            )
        except Exception as e:
            self.logger.error(f"LLM query failed: {str(e)}")
            raise

    async def _query_llm_async(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
        system_message: Optional[str] = None,
    ) -> str:
        """Asynchronous LLM query."""
        try:
            return await self.llm_client.query_async(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                system_message=system_message,
            )
        except Exception as e:
            self.logger.error(f"Async LLM query failed: {str(e)}")
            raise

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
        """Parse LLM response for action decision."""
        try:
            # Look for DECISION: line
            if "DECISION:" not in response:
                self.logger.warning(
                    f"No DECISION: found in response: {response[:100]}..."
                )
                return "fold"

            decision_line = next(
                line for line in response.split("\n") if "DECISION:" in line
            )
            action = decision_line.split("DECISION:")[1].strip().lower().split()[0]

            # Validate action
            valid_actions = ["fold", "call", "raise"]
            if action not in valid_actions:
                self.logger.warning(f"Invalid action '{action}' in response")
                return "fold"

            return action

        except Exception as e:
            self.logger.error(f"Error parsing decision: {str(e)}")
            return "fold"

    def _validate_bet_amount(self, action: str) -> int:
        """Validate and adjust bet amount."""
        try:
            if action.startswith("raise"):
                try:
                    amount = int(action.split()[1])
                    return max(100, amount)  # Minimum raise of 100
                except (IndexError, ValueError):
                    return 100  # Default raise amount
            return 0  # For fold/call

        except Exception as e:
            self.logger.error(f"Error validating bet amount: {str(e)}")
            return 0

    def _create_message_prompt(self, game_state: Union[str, Dict[str, Any]]) -> str:
        """Create prompt for message generation."""
        # Get recent table history
        table_history = (
            "\n".join(self.table_history[-3:])
            if self.table_history
            else "No recent history"
        )

        # Get relevant memories
        memories = self.get_relevant_memories(
            self._create_memory_query(game_state)
            if isinstance(game_state, dict)
            else game_state
        )
        memory_context = (
            "\n".join(f"- {m['text']}" for m in memories)
            if memories
            else "No relevant memories"
        )

        # Format recent conversation history
        recent_conversation = (
            "\n".join(
                f"{msg['sender']}: {msg['message']}"
                for msg in self.conversation_history[-3:]
            )
            if self.conversation_history
            else "No recent conversation"
        )

        return STRATEGIC_MESSAGE_PROMPT.format(
            strategy_style=self.strategy_style,
            game_state=game_state,
            position=getattr(self, "position", "unknown"),
            recent_actions=self._format_recent_actions(),
            opponent_patterns=self._get_opponent_patterns(),
            communication_style=self.communication_style,
            emotional_state=self.emotional_state,
            table_history=table_history,
            recent_observations=(
                "\n".join(str(p) for p in self.perception_history[-3:])
                if self.perception_history
                else "No recent observations"
            ),
            memory_context=memory_context,
            recent_conversation=recent_conversation,
        )

    def _parse_message(self, response: str) -> str:
        """Parse LLM response for message content."""
        try:
            # Extract message content
            if "MESSAGE:" not in response:
                return ""

            message_line = next(
                line for line in response.split("\n") if line.startswith("MESSAGE:")
            )

            message = message_line.replace("MESSAGE:", "").strip()

            # Store in table history
            self.table_history.append(f"{self.name}: {message}")

            return message

        except Exception as e:
            self.logger.error(f"Error parsing message: {str(e)}")
            return ""

    def _create_decision_prompt(self, game_state: Union[str, Dict[str, Any]]) -> str:
        """Create the decision prompt with current game state and strategy."""
        # Get current plan if available
        current_plan = None
        if self.use_planning and hasattr(self, "strategy_planner"):
            current_plan = self.strategy_planner.current_plan

        # Format plan information for strategy prompt
        strategy_prompt = f"\nCurrent Plan: {current_plan.dict() if current_plan else 'No active plan'}"

        # Get relevant memories
        memories = self.get_relevant_memories(
            self._create_memory_query(game_state)
            if isinstance(game_state, dict)
            else game_state
        )
        memory_info = (
            "\n".join(f"- {m['text']}" for m in memories)
            if memories
            else "No relevant memories"
        )

        # Format opponent info if available
        opponent_info = (
            self._get_opponent_patterns()
            if self.use_opponent_modeling
            else "No opponent modeling"
        )

        return DECISION_PROMPT.format(
            strategy_style=self.strategy_style,
            game_state=game_state,
            strategy_prompt=strategy_prompt,  # Pass strategy_prompt instead of plan_info
            memory_info=memory_info,
            opponent_info=opponent_info,
            personality_traits=self.personality_traits,
        )

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

    def cleanup(self):
        """Cleanup resources."""
        # Get final metrics
        metrics = self.llm_client.get_metrics()
        self.logger.info(f"Final LLM metrics for {self.name}: {metrics}")

        # Cleanup memory store
        if hasattr(self, "memory_store"):
            self.memory_store.close()
