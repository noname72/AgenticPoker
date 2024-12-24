import asyncio
import logging
import os
import random
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

from agents.strategy_cards import StrategyManager
from agents.strategy_planner import StrategyPlanner
from data.enums import StrategyStyle
from data.memory import ChromaMemoryStore
from exceptions import LLMError, OpenAIError
from game.player import Player

# Load environment variables
load_dotenv()

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
        self, game_state: str, opponent_message: Optional[str] = None
    ) -> str:
        """Base method for deciding actions."""
        return "call"  # Default safe action instead of raising NotImplementedError

    def get_message(self, game_state: str) -> str:
        """Base method for generating messages."""
        return ""

    def decide_draw(self) -> List[int]:
        """Base method for deciding which cards to draw."""
        return []


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
        strategy_style: Optional[str] = None,
        personality_traits: Optional[Dict[str, float]] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        use_reasoning: bool = True,
        use_reflection: bool = True,
        use_planning: bool = True,
        use_opponent_modeling: bool = False,
        use_reward_learning: bool = False,
        learning_rate: float = 0.1,
        config: Optional[Dict] = None,
        session_id: Optional[str] = None,
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
        """
        super().__init__(name, chips)
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
        self.strategy_style = strategy_style or random.choice(
            [s.value for s in StrategyStyle]
        )
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.personality_traits = personality_traits or {
            "aggression": 0.5,
            "bluff_frequency": 0.5,
            "risk_tolerance": 0.5,
        }

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = OpenAI(api_key=api_key)

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

    def __del__(self):
        """Cleanup when agent is destroyed.

        Ensures proper cleanup of resources by:
        1. Clearing all in-memory data
        2. Closing and deleting memory store
        3. Cleaning up OpenAI client
        """
        try:
            # First clear all in-memory data
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

            # Then clean up memory store - do this before client cleanup
            if hasattr(self, "memory_store"):
                try:
                    # Don't clear the memories, just close the connection
                    self.memory_store.close()
                except Exception as e:
                    if "Python is likely shutting down" not in str(e):
                        logging.warning(f"Error cleaning up memory store: {str(e)}")
                finally:
                    del self.memory_store

            # Finally clean up OpenAI client
            if hasattr(self, "client"):
                try:
                    del self.client
                except Exception as e:
                    if "Python is likely shutting down" not in str(e):
                        logging.warning(f"Error cleaning up OpenAI client: {str(e)}")

        except Exception as e:
            if "Python is likely shutting down" not in str(e):
                logging.error(f"Error in cleanup: {str(e)}")

    def _get_decision_prompt(self, game_state: str) -> str:
        """Creates a decision prompt combining strategy and game state."""
        strategy_prompt = self.strategy_manager.get_complete_prompt(
            {
                "chips": self.chips,
                "is_bubble": self._is_bubble_situation(game_state),
            }
        )

        return f"""You are a {self.strategy_style} poker player. You must respond with exactly one action.

{strategy_prompt}

Current situation:
{game_state}

Respond ONLY in this format:
DECISION: <action> <brief reason>
where <action> must be exactly one of: fold, call, raise

Example responses:
DECISION: fold weak hand against aggressive raise
DECISION: call decent draw with good pot odds
DECISION: raise strong hand in position

What is your decision?
"""

    def decide_action(
        self, game_state: str, opponent_message: Optional[str] = None
    ) -> str:
        """Uses strategy-aware prompting to make decisions."""
        try:
            # Use strategy planner if enabled
            if self.use_planning:
                self.logger.info(f"[{self.name}] Using strategy planner for decision")
                # Get plan and execute action
                plan = self.strategy_planner.plan_strategy(game_state, self.chips)
                action = self.strategy_planner.execute_action(game_state)
                self.logger.info(
                    f"[{self.name}] Strategy plan: {plan['approach']} -> Action: {action}"
                )
                return action

            self.logger.info(f"[{self.name}] Using basic decision making")
            # Fallback to basic decision making if planning disabled
            relevant_memories = self.memory_store.get_relevant_memories(
                query=game_state,
                k=2,
            )

            # Format memories for prompt
            memory_context = ""
            if relevant_memories:
                memory_context = "\nRecent relevant experiences:\n" + "\n".join(
                    [f"- {mem['text']}" for mem in relevant_memories]
                )

            prompt = self._get_decision_prompt(game_state + memory_context)
            response = self._query_llm(prompt)

            if "DECISION:" not in response:
                raise ValueError("No decision found in response")

            action = response.split("DECISION:")[1].strip().split()[0]
            return self._normalize_action(action)

        except Exception as e:
            self.logger.error(f"Decision error: {str(e)}")
            return "call"  # Safe fallback

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
        """Get a strategic message from the agent."""
        prompt = f"""
        You are a {self.strategy_style} poker player.
        
        Current situation:
        {game_state}
        
        CRITICAL RULES:
        1. Start with exactly "MESSAGE: "
        2. Maximum 5 words after "MESSAGE: "
        3. No punctuation except periods
        4. No pronouns (I, you, we, etc)
        
        Valid examples:
        MESSAGE: All in with strong hand
        MESSAGE: Playing tight this round
        MESSAGE: Time to bluff big
        
        Invalid examples:
        MESSAGE: I'm going to bluff big time now!  (too long, has pronouns)
        MESSAGE: Let's see who's brave enough  (has pronouns)
        MESSAGE: Time to show my dominance at the table  (too long)
        
        Respond with exactly one message following these rules.
        """

        try:
            response = self._query_llm(prompt).strip()

            # Extract and validate message
            if "MESSAGE:" in response:
                message = response.split("MESSAGE:")[1].strip()
                # Validate length
                words = message.split()
                if len(words) > 5:
                    message = " ".join(words[:5])
                # Remove punctuation except periods
                message = "".join(
                    c for c in message if c.isalnum() or c.isspace() or c == "."
                )
                self.last_message = message
                return message

            self.logger.warning(f"Invalid message format: {response}")
            return "Thinking about next move"

        except Exception as e:
            self.logger.error(f"Error generating message: {e}")
            return "Thinking about next move"

    def decide_draw(self) -> List[int]:
        """Decide which cards to discard and draw new ones."""
        game_state = f"Hand: {self.hand.show()}"

        prompt = f"""You are a {self.strategy_style} poker player deciding which cards to discard.

Current situation:
{game_state}

CRITICAL RULES:
1. You MUST include a line starting with "DISCARD:" followed by:
   - [x,y] for multiple positions
   - [x] for single position
   - none for keeping all cards
2. Use ONLY card positions (0-4 from left to right)
3. Maximum 3 cards can be discarded
4. Format must be exactly as shown in examples

Example responses:
ANALYSIS:
Pair of Kings, weak kickers
Should discard both low cards

DISCARD: [0,1]

ANALYSIS:
Strong two pair, keep everything

DISCARD: none

ANALYSIS:
Weak high card only
Discard three cards for new draw

DISCARD: [2,3,4]

Current hand positions:
Card 0: {self.hand.cards[0] if len(self.hand.cards) > 0 else 'N/A'}
Card 1: {self.hand.cards[1] if len(self.hand.cards) > 1 else 'N/A'}
Card 2: {self.hand.cards[2] if len(self.hand.cards) > 2 else 'N/A'}
Card 3: {self.hand.cards[3] if len(self.hand.cards) > 3 else 'N/A'}
Card 4: {self.hand.cards[4] if len(self.hand.cards) > 4 else 'N/A'}

What is your discard decision?
"""
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

    def perceive(self, game_state: str, opponent_message: str) -> Dict[str, Any]:
        """Process and store new game information in memory systems.

        Updates both short-term memory (recent events) and long-term memory (ChromaDB)
        with new game states and messages for future reference.

        Args:
            game_state: Current state of the game
            opponent_message: Message from opponent

        Returns:
            dict: Perception entry containing game state, message, and timestamp

        Note:
            Maintains limited-size short-term memory and unlimited long-term memory.
        """
        # Create perception entry
        perception = {
            "game_state": game_state,
            "opponent_message": opponent_message,
            "timestamp": time.time(),
        }

        # Store in short-term memory
        if len(self.perception_history) >= self.short_term_limit:
            self.perception_history.pop(0)
        self.perception_history.append(perception)

        # Store in long-term memory
        memory_text = f"Game State: {game_state}\nOpponent Message: {opponent_message}"
        self.memory_store.add_memory(
            text=memory_text,
            metadata={
                "type": "perception",
                "timestamp": time.time(),
                "strategy_style": self.strategy_style,
            },
        )

        # Handle conversation history
        if opponent_message:
            if len(self.conversation_history) >= self.short_term_limit:
                self.conversation_history.pop(0)
            self.conversation_history.append(
                {
                    "sender": "opponent",
                    "message": opponent_message,
                    "timestamp": time.time(),
                }
            )

            # Store conversation in long-term memory
            self.memory_store.add_memory(
                text=opponent_message,
                metadata={
                    "type": "conversation",
                    "sender": "opponent",
                    "timestamp": time.time(),
                    "strategy_style": self.strategy_style,
                },
            )

        return perception

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

        prompt = f"""You are a {self.strategy_style} poker player.
Your response must be a single short message (max 10 words) that fits your style.

Game State: {game_state}
Recent Observations: {self.perception_history[-3:] if self.perception_history else "None"}
Relevant Memories: {memory_context}
Recent Chat: {recent_conversation}

Example responses:
- "I always bet big with strong hands!"
- "Playing it safe until I see weakness."
- "You can't read my unpredictable style!"

Your table talk message:"""

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

    def _normalize_action(self, action: str) -> str:
        """Normalize the LLM's action response to a valid action.

        Processes and standardizes action strings from LLM responses into
        valid poker actions. Handles variations and embedded actions in sentences.

        Args:
            action (str): Raw action string from LLM

        Returns:
            str: Normalized action ('fold', 'call', or 'raise')
            None: If action cannot be normalized

        Note:
            - Normalizes 'check' to 'call'
            - Normalizes 'bet' to 'raise'
            - Handles actions embedded in sentences
            - Strips punctuation and quotes
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
            prompt = f"""
            You are a {self.strategy_style} poker player.
            
            Current situation:
            {game_state}
            Opponent message: {opponent_message or 'None'}
            
            CRITICAL RULES:
            1. Start with "ANALYSIS:" followed by 1-3 short lines
            2. Then exactly "DECISION: <action>" where action is fold/call/raise
            3. No additional text or explanations
            4. No bet amounts or other details
            
            Valid example:
            ANALYSIS:
            Strong hand in position
            Good pot odds
            
            DECISION: raise
            
            Invalid examples:
            DECISION: raise to 300  (no amounts allowed)
            DECISION: raise because I have a strong hand  (no explanations)
            DECISION: check  (not a valid action)
            """

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
        """Asynchronous query to OpenAI's GPT model with error handling and timeout."""
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

    def _query_llm(self, prompt: str) -> str:
        """Query LLM with retry mechanism and error handling.

        Makes repeated attempts to get a response from the language model,
        implementing exponential backoff and comprehensive error handling.

        Args:
            prompt (str): The prompt to send to the language model

        Returns:
            str: Response from the language model

        Raises:
            LLMError: If all retry attempts fail or other unrecoverable error occurs

        Note:
            Uses self.max_retries and self.retry_delay for retry configuration.
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                self.logger.info(
                    "[LLM Query] Attempt %d for %s", attempt + 1, self.name
                )
                self.logger.debug("[LLM Query] Prompt: %s", prompt)

                result = self._query_gpt(prompt)
                self.logger.info("[LLM Query] Response: %s", result)
                return result

            except OpenAIError as e:
                last_error = e
                self.logger.error(
                    "[LLM Query] OpenAI error on attempt %d: %s",
                    attempt + 1,
                    str(e),
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue

        self.logger.error(
            "[LLM Query] All %d attempts failed for %s", self.max_retries, self.name
        )
        raise LLMError(f"Failed after {self.max_retries} attempts") from last_error

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
        """Reset agent's state for a new game.

        Clears all temporary state including:
            - Perception history
            - Conversation history
            - Current plan
            - Memory store
            - Last message

        Note:
            Reinitializes memory store with clean collection.
            Logs reset operation for debugging.
        """
        if hasattr(self, "memory_store"):
            self.memory_store.close()
        self.perception_history = []
        self.conversation_history = []
        self.last_message = ""
        if self.use_planning:
            self.current_plan = None
            self.plan_expiry = 0

        # Reinitialize memory store
        collection_name = f"agent_{self.name.lower().replace(' ', '_')}_memory"
        self.memory_store = ChromaMemoryStore(collection_name)
        self.logger.info(f"[Reset] Agent {self.name} reset for new game")

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
                "approach": self.current_plan["approach"],
                "expires_in": max(0, self.plan_expiry - time.time()),
            }
        return stats

    def plan_strategy(self, game_state: str) -> Dict[str, Any]:
        """Generate or update the agent's strategic plan.

        Creates a short-term strategic plan considering the agent's traits, current
        game state, and recent history. Plans include approach, bet sizing, and
        thresholds for actions.

        Args:
            game_state: Current state of the game

        Returns:
            dict: Strategic plan containing:
                - approach: Overall strategy (aggressive/defensive/deceptive/balanced)
                - reasoning: Explanation of the chosen approach
                - bet_sizing: Preferred bet size (small/medium/large)
                - bluff_threshold: Probability threshold for bluffing
                - fold_threshold: Probability threshold for folding

        Note:
            Plans expire after a set duration or when significant game changes occur.
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
        planning_prompt = f"""
        You are a {self.strategy_style} poker player planning your strategy.
        
        Current situation:
        {game_state}
        
        Create a strategic plan using this exact format:
        {{
            "approach": "<aggressive/balanced/defensive>",
            "reasoning": "<brief explanation>",
            "bet_sizing": "<small/medium/large>",
            "bluff_threshold": <float 0-1>,
            "fold_threshold": <float 0-1>
        }}
        
        Example:
        {{
            "approach": "aggressive",
            "reasoning": "Strong hand, weak opponents",
            "bet_sizing": "large",
            "bluff_threshold": 0.7,
            "fold_threshold": 0.2
        }}
        """

        try:
            response = self._query_llm(planning_prompt)
            plan = eval(response.strip())  # Safe since we control LLM output format

            # Update plan tracking
            self.current_plan = plan
            self.plan_expiry = current_time + self.plan_duration

            self.logger.info(
                f"[Planning] {self.name} adopted {plan['approach']} approach: {plan['reasoning']}"
            )
            return plan

        except Exception as e:
            self.logger.error(f"Planning failed: {str(e)}")
            # Fallback plan
            return {
                "approach": "balanced",
                "reasoning": "Error in planning, falling back to balanced approach",
                "bet_sizing": "medium",
                "bluff_threshold": 0.5,
                "fold_threshold": 0.3,
            }

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
        execution_prompt = f"""
        You are a {self.strategy_style} poker player following this plan:
        Approach: {plan['approach']}
        Reasoning: {plan['reasoning']}
        
        Current situation:
        {game_state}
        
        Given your {plan['approach']} approach:
        1. Evaluate if the situation matches your plan
        2. Consider pot odds and immediate action costs
        3. Factor in your bluff_threshold ({plan['bluff_threshold']}) and fold_threshold ({plan['fold_threshold']})
        
        Respond with EXECUTE: <fold/call/raise> and brief reasoning
        """

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
        """Parse the decision from LLM response with strict format checking."""
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
        """Parse the discard positions with strict format checking."""
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

            return sorted(positions)

        except Exception as e:
            logger.error(f"Error parsing discard positions: {e}")
            return []
