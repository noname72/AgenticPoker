import asyncio
import logging
import os
import random
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI

from data.enums import StrategyStyle
from data.memory import ChromaMemoryStore
from exceptions import LLMError, OpenAIError
from game.player import Player

# Load environment variables
load_dotenv()


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
        """Base method for deciding actions - should be overridden."""
        raise NotImplementedError

    def get_message(self, game_state: str) -> str:
        """Base method for generating messages - should be overridden."""
        return ""

    def decide_draw(self) -> List[int]:
        """Base method for deciding which cards to draw - should be overridden."""
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
        """
        super().__init__(name, chips)
        self.use_reasoning = use_reasoning
        self.use_reflection = use_reflection
        self.use_planning = use_planning

        self.last_message = ""
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
            self.current_plan: Optional[Dict[str, Any]] = None
            self.plan_expiry: float = 0
            self.plan_duration: float = 30.0  # Plan lasts for 30 seconds by default

        # Initialize memory store with sanitized name for collection
        collection_name = f"agent_{name.lower().replace(' ', '_')}_memory"
        self.memory_store = ChromaMemoryStore(collection_name)

        # Keep short-term memory in lists for immediate context
        self.short_term_limit = 3
        self.perception_history: List[Dict[str, Any]] = []
        self.conversation_history: List[Dict[str, Any]] = []

    def __del__(self):
        """Cleanup when agent is destroyed."""
        if hasattr(self, "memory_store"):
            self.memory_store.close()

    def decide_action(
        self, game_state: str, opponent_message: Optional[str] = None
    ) -> str:
        """Make a strategic decision based on current game state and opponent's message.

        Uses either planning-based or direct decision making depending on configuration.
        Enriches game state with hand evaluation and updates perception history.

        Args:
            game_state: Current state of the game including pot, bets, etc.
            opponent_message: Optional message from opponent to consider

        Returns:
            str: Selected action ('fold', 'call', or 'raise')

        Note:
            When planning is enabled, follows a strategic plan with periodic replanning.
            Otherwise uses direct LLM querying for decisions.
        """
        # Enrich game state
        hand_eval = self.hand.evaluate() if self.hand.cards else "No cards"
        enriched_state = f"{game_state}, Hand evaluation: {hand_eval}"

        # Update perception
        self.perceive(enriched_state, opponent_message or "")

        if self.use_planning:
            # Use planning-based decision making
            plan = self.plan_strategy(enriched_state)
            action = self.execute_action(plan, enriched_state)
            self.logger.info(
                f"{self.name} executes {action} following {plan['approach']} strategy"
            )
        else:
            # Use direct decision making
            action = self.get_action(enriched_state, opponent_message)
            self.logger.info(f"{self.name} decides to {action}")

        return action

    def get_message(self, game_state: str) -> str:
        """Get a strategic message from the agent."""
        # Enrich game state with hand information if available
        if self.hand.cards:
            game_state = f"{game_state}, Hand: {self.hand.show()}"
        return self._get_strategic_message(game_state)

    def decide_draw(self) -> List[int]:
        """Decide which cards to discard and draw new ones."""
        game_state = f"Hand: {self.hand.show()}"

        prompt = f"""
        You are a {self.strategy_style} poker player.
        Current hand: {game_state}
        
        Which cards should you discard? Consider:
        1. Pairs or potential straights/flushes
        2. High cards worth keeping
        3. Your strategy style
        
        Respond with only the indices (0-4) of cards to discard, separated by spaces.
        Example: "0 2 4" to discard first, third, and last cards.
        Respond with "none" to keep all cards.
        """

        response = self._query_llm(prompt).strip().lower()
        if response == "none":
            return []

        try:
            indices = [int(i) for i in response.split()]
            return [i for i in indices if 0 <= i <= 4]
        except:
            # If parsing fails, make a simple decision based on pairs
            ranks = [card.rank for card in self.hand.cards]
            return [i for i, rank in enumerate(ranks) if ranks.count(rank) == 1]

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
        """Enhanced message generation with memory retrieval.

        Generates strategic messages by considering game state, memory context,
        and recent conversation history. Uses LLM to craft messages that align
        with the agent's strategy style and personality traits.

        Args:
            game_state (str): Current state of the game including hand information

        Returns:
            str: Strategic message to influence opponent

        Note:
            - Stores generated message in both short and long-term memory
            - Considers up to 5 recent conversation entries
            - Limits message length to 10 words
        """
        # Get relevant memories
        query = f"Strategy: {self.strategy_style}, Game State: {game_state}"
        relevant_memories = self.memory_store.get_relevant_memories(query)

        # Format memories for prompt
        memory_context = "\n".join(
            [f"Memory {i+1}: {mem['text']}" for i, mem in enumerate(relevant_memories)]
        )

        # Format recent conversation
        recent_conversation = "\n".join(
            [
                f"{msg['sender']}: {msg['message']}"
                for msg in self.conversation_history[-5:]
            ]
        )

        prompt = f"""
        You are a {self.strategy_style} poker player in Texas Hold'em.
        
        Current situation:
        Game State: {game_state}
        Your recent observations: {self.perception_history[-3:] if self.perception_history else "None"}
        
        Relevant memories:
        {memory_context}
        
        Recent conversation:
        {recent_conversation if self.conversation_history else "No previous conversation"}
        
        Generate a strategic message to influence your opponent. Your personality is {self.strategy_style}.
        
        Your message should:
        1. Match your strategy style
        2. Be under 10 words
        3. Try to influence your opponent
        4. Consider the conversation history and maintain consistency
        
        What message will you send?
        """

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
        """Determine the next action based on the game state and opponent's message.

        Uses either simple or reasoning-based decision making based on configuration.
        Can include self-reflection mechanism to validate decisions.

        Args:
            game_state (str): Current state of the game
            opponent_message (Optional[str]): Message from opponent, if any

        Returns:
            str: Selected action ('fold', 'call', or 'raise')

        Note:
            - Falls back to 'call' if decision making fails
            - Uses personality traits to influence decisions
            - Implements optional reasoning and reflection steps
        """
        try:
            if not self.use_reasoning:
                # Use simple prompt without reasoning
                simple_prompt = f"""
                You are a {self.strategy_style} poker player with specific traits:
                - Aggression: {self.personality_traits['aggression']:.1f}/1.0
                - Bluff Frequency: {self.personality_traits['bluff_frequency']:.1f}/1.0
                - Risk Tolerance: {self.personality_traits['risk_tolerance']:.1f}/1.0
                
                Current situation:
                Game State: {game_state}
                Opponent's Message: '{opponent_message or "nothing"}'
                Recent History: {self.perception_history[-3:] if self.perception_history else []}
                
                Respond with exactly one word (fold/call/raise).
                """
                raw_action = self._query_llm(simple_prompt)
                initial_action = self._normalize_action(raw_action)

                if initial_action is None:
                    self.logger.warning(
                        f"LLM returned invalid action '{raw_action}', falling back to 'call'"
                    )
                    return "call"

                return initial_action

            # Use reasoning prompt
            reasoning_prompt = f"""
            You are a {self.strategy_style} poker player with specific traits:
            - Aggression: {self.personality_traits['aggression']:.1f}/1.0
            - Bluff Frequency: {self.personality_traits['bluff_frequency']:.1f}/1.0
            - Risk Tolerance: {self.personality_traits['risk_tolerance']:.1f}/1.0
            
            Current situation:
            Game State: {game_state}
            Opponent's Message: '{opponent_message or "nothing"}'
            Recent History: {self.perception_history[-3:] if self.perception_history else []}
            
            Think through this step by step:
            1. What does my hand evaluation tell me about my chances?
            2. How does my strategy style influence this decision?
            3. What have I learned from the opponent's recent behavior?
            4. What are the pot odds and risk/reward considerations?
            5. How does this align with my personality traits?
            
            Provide your reasoning, then conclude with "DECISION: <action>", 
            where action is exactly one word (fold/call/raise).
            """

            reasoning = self._query_llm(reasoning_prompt)

            # Extract the decision from the reasoning
            decision_line = [
                line for line in reasoning.split("\n") if "DECISION:" in line
            ]
            if not decision_line:
                self.logger.warning("No clear decision found in reasoning")
                return "call"

            raw_action = decision_line[0].split("DECISION:")[1].strip()
            initial_action = self._normalize_action(raw_action)

            if initial_action is None:
                self.logger.warning(
                    f"LLM returned invalid action '{raw_action}', falling back to 'call'"
                )
                return "call"

            if not self.use_reflection:
                return initial_action

            # Use reflection mechanism
            reflection_prompt = f"""
            You just decided to {initial_action} with this reasoning:
            {reasoning}
            
            Reflect on this decision:
            1. Is it consistent with my {self.strategy_style} style?
            2. Does it match my personality traits?
            3. Could this be a mistake given the current situation?
            
            If you find any inconsistencies, respond with "REVISE: <new_action>"
            If the decision is sound, respond with "CONFIRM: {initial_action}"
            """

            reflection = self._query_llm(reflection_prompt).strip()

            if reflection.startswith("REVISE:"):
                revised_action = self._normalize_action(
                    reflection.split("REVISE:")[1].strip()
                )
                if revised_action:
                    self.logger.info(
                        f"{self.name} revised action from {initial_action} to {revised_action}"
                    )
                    return revised_action

            return initial_action

        except LLMError as e:
            self.logger.error(f"LLM error in get_action: {str(e)}")
            return "call"

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
                        model="gpt-3.5-turbo",
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

    def analyze_opponent(self) -> Dict[str, Any]:
        """Analyze opponent's behavioral patterns and playing style.

        Reviews historical interactions and game states to identify patterns
        in opponent's betting, bluffing, and messaging behavior.

        Returns:
            dict: Analysis results containing:
                - patterns (str): Identified behavior pattern
                - threat_level (str): Assessed threat level (low/medium/high)

        Note:
            Returns default values if insufficient history available.
            Uses perception_history for pattern analysis.
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
            self.logger.error(
                "[Opponent Analysis] Error parsing LLM response: %s", str(e)
            )

        return {"patterns": "unknown", "threat_level": "medium"}

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
        You are a {self.strategy_style} poker player with these traits:
        - Aggression: {self.personality_traits['aggression']:.1f}/1.0
        - Bluff Frequency: {self.personality_traits['bluff_frequency']:.1f}/1.0
        - Risk Tolerance: {self.personality_traits['risk_tolerance']:.1f}/1.0

        Current situation:
        {game_state}
        Recent history: {self.perception_history[-3:] if self.perception_history else "None"}
        
        Develop a short-term strategic plan. Consider:
        1. Your chip stack and position
        2. Recent opponent behavior
        3. Your personality traits
        4. Risk/reward balance
        
        Respond in this JSON format:
        {{
            "approach": "<aggressive/defensive/deceptive/balanced>",
            "reasoning": "<brief explanation>",
            "bet_sizing": "<small/medium/large>",
            "bluff_threshold": <0.0-1.0>,
            "fold_threshold": <0.0-1.0>
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
