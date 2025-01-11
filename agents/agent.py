import logging
import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from agents.llm_client import LLMClient
from agents.prompts import DECISION_PROMPT, DISCARD_PROMPT
from agents.strategy_cards import StrategyManager
from agents.strategy_planner import StrategyPlanner
from config import GameConfig
from data.memory import ChromaMemoryStore
from data.model import Game
from data.types.action_response import ActionResponse, ActionType
from game.evaluator import HandEvaluation
from game.player import Player

logger = logging.getLogger(__name__)


class Agent(Player):
    """An intelligent poker agent that uses LLM-based decision making and various cognitive modules.

    This agent extends the base Player class with sophisticated decision-making capabilities including:
    - LLM-based reasoning for actions and table talk
    - Strategic planning and adaptation
    - Memory management for game history
    - Opponent modeling and analysis
    - Reward-based learning

    Attributes:
        name (str): The agent's name
        chips (int): Current chip count
        strategy_style (str): Base strategy style (e.g. "Aggressive Bluffer")
        use_reasoning (bool): Whether to use LLM reasoning module
        use_reflection (bool): Whether to use reflection on past decisions
        use_planning (bool): Whether to use strategic planning
        use_opponent_modeling (bool): Whether to track and analyze opponents
        use_reward_learning (bool): Whether to learn from action outcomes
        learning_rate (float): Rate of strategy adaptation (0-1)
        communication_style (str): Style of table talk (e.g. "Intimidating")
        emotional_state (str): Current emotional context for decisions

    The agent can be used either with explicit cleanup:
        agent = Agent("Bot1")
        try:
            # Use agent
        finally:
            agent.close()

    Or as a context manager (preferred):
        with Agent("Bot2") as agent:
            # Use agent

    Note:
        - Requires OpenAI API key for LLM functionality
        - Uses ChromaDB for persistent memory storage
        - Memory and resources are cleaned up automatically when using context manager
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
        use_reward_learning: bool = True,
        learning_rate: float = 0.1,
        config: GameConfig = None,
        session_id: str = None,
        communication_style: str = "Intimidating",
    ):
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
                plan_duration=30.0,
            )
        else:
            self.strategy_planner = None

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
        #! is this needed if we have strategy planner???
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
                        logger.warning(f"Error cleaning up memory store: {str(e)}")
                finally:
                    del self.memory_store

            # Clean up OpenAI client
            if hasattr(self, "client"):
                try:
                    del self.client
                except Exception as e:
                    if "Python is likely shutting down" not in str(e):
                        logger.warning(f"Error cleaning up OpenAI client: {str(e)}")

        except Exception as e:
            if "Python is likely shutting down" not in str(e):
                logger.error(f"Error in cleanup: {str(e)}")

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

    def decide_action(self, game: "Game") -> ActionResponse:
        """Determine the next poker action based on the current game state and strategy.

        This method serves as the main decision-making entry point that:
        1. Evaluates the agent's current hand
        2. Uses the StrategyPlanner if available for sophisticated decision-making
        3. Falls back to basic LLM-based decision making if no planner is present

        Args:
            game: The current game state containing information about:
                - Table cards
                - Pot size
                - Player positions
                - Betting history
                - Other relevant game information

        Returns:
            ActionResponse: A structured response containing:
                - action: str - The chosen action ('fold', 'call', or 'raise')
                - amount: int - The bet amount (if action is 'raise')

        Note:
            The decision-making process prioritizes using the StrategyPlanner
            for more sophisticated, plan-based decisions. Only falls back to
            basic LLM decision-making if the planner is disabled or unavailable.
        """
        # Get hand evaluation before making decision
        hand_eval: HandEvaluation = self.hand.evaluate() if self.hand else None

        if self.strategy_planner:
            return self.strategy_planner.get_action(game, hand_eval)

        # Fallback to basic decision making if no strategy planner
        return self._basic_decision(game, hand_eval)

    def _basic_decision(
        self, game: "Game", hand_eval: Optional[HandEvaluation] = None
    ) -> ActionResponse:
        """Make a poker decision using LLM-based reasoning when strategy planner is unavailable.

        This method serves as a fallback decision-making mechanism that:
        1. Creates a decision prompt incorporating game state and hand evaluation
        2. Queries the LLM with retry logic
        3. Parses and validates the LLM's response
        4. Converts the decision into a valid ActionResponse

        Args:
            game: Current game state including table cards, pot size, and betting information
            hand_eval: Optional evaluation of the agent's current hand strength and potential

        Returns:
            ActionResponse: Contains the chosen action ('fold', 'call', or 'raise') and
                bet amount if applicable

        Note:
            - Expected LLM response format is "DECISION: <action> [amount]"
            - Valid actions are 'fold', 'call', or 'raise <amount>'
            - Defaults to 'fold' on invalid responses or errors
            - For 'raise' actions, amount must be a positive integer
            - Invalid raise formats/amounts default to 'call'
        """
        try:
            # Create decision prompt
            prompt = self._create_decision_prompt(game, hand_eval)

            # Add system message for strategy context
            system_message = (
                f"You are a {self.strategy_style} poker player making decisions."
            )

            # Query LLM with retry logic
            response = self.llm_client.query(
                prompt=prompt, temperature=0.7, system_message=system_message
            ).strip()  # Strip whitespace from full response

            # Debug logging
            logger.debug(f"Raw LLM response:\n{response}")

            # Parse and validate response
            if "DECISION:" not in response:
                logger.warning(f"No DECISION: found in response: {response[:100]}...")
                return ActionResponse(action_type=ActionType.FOLD)

            decision_line = next(
                line.strip() for line in response.split("\n") if "DECISION:" in line
            )
            parts = decision_line.replace("DECISION:", "").strip().split()
            action = parts[0].lower()

            # Validate action more strictly
            if action not in ["fold", "call", "raise"]:
                logger.warning(f"Invalid action '{action}' in response")
                return ActionResponse(action_type=ActionType.FOLD)

            # Handle raise amount more strictly
            if action == "raise":
                try:
                    if len(parts) != 2:
                        logger.warning("Raise command must have exactly one number")
                        return ActionResponse(action_type=ActionType.CALL)

                    amount = int(parts[1])
                    if amount <= 0:
                        logger.warning("Raise amount must be positive")
                        return ActionResponse(action_type=ActionType.CALL)

                    return ActionResponse(
                        action_type=ActionType.RAISE, raise_amount=amount
                    )
                except ValueError:
                    logger.warning("Invalid raise amount format")
                    return ActionResponse(action_type=ActionType.CALL)

            # Map string actions to ActionType enum
            action_map = {
                "fold": ActionType.FOLD,
                "call": ActionType.CALL,
            }

            return ActionResponse(action_type=action_map[action])

        except Exception as e:
            logger.error(f"Error in decide_action: {str(e)}")
            return ActionResponse(action_type=ActionType.FOLD)

    def _create_decision_prompt(
        self, game: "Game", hand_eval: Optional[HandEvaluation] = None
    ) -> str:
        #! is this needed???
        """Creates a formatted prompt for the LLM to make poker decisions.

        Combines game state, hand evaluation, memory context, opponent modeling,
        and agent personality traits into a structured prompt for decision-making.

        Args:
            game: Current game state including table cards, pot size, and player positions
            hand_eval: Optional evaluation of the agent's current hand strength

        Returns:
            str: A formatted prompt string using the DECISION_PROMPT template

        Note:
            The prompt includes:
            - Agent's strategy style and personality traits
            - Current game state and hand evaluation
            - Relevant historical memories of past hands/decisions
            - Opponent behavior patterns (if opponent modeling is enabled)
        """

        # Get relevant memories
        # memories = self.get_relevant_memories(self._create_memory_query(game))
        # memory_info = (
        #     "\n".join(f"- {m['text']}" for m in memories)
        #     if memories
        #     else "No relevant memories"
        # )

        # Format opponent info if available
        # opponent_info = (
        #     self._get_opponent_patterns()
        #     if self.use_opponent_modeling
        #     else "No opponent modeling"
        # )

        return DECISION_PROMPT.format(
            strategy_style=self.strategy_style,
            game_state=game.get_state(),
            hand_eval=hand_eval,
            memory_info=None,
            opponent_info=None,
            personality_traits=self.personality_traits,
        )

    def get_message(self, game) -> str:
        """Generate table talk using LLM.

        Args:
            game: Current game state

        Returns:
            str: A message for table talk, or empty string if generation fails
        """
        try:
            # Create message prompt
            game_state = game.get_state()
            prompt = self._create_message_prompt(game_state)

            system_message = (
                f"You are a {self.communication_style} {self.strategy_style} "
                f"poker player engaging in table talk."
            )

            # Query LLM with lower temperature for more consistent messaging
            response = self.llm_client.query(
                prompt=prompt, temperature=0.5, system_message=system_message
            )

            # Parse response - look for MESSAGE: prefix
            if "MESSAGE:" not in response:
                logger.warning("No MESSAGE: found in response")
                return "..."  # Return a default message instead of empty string

            # Extract the message part after MESSAGE:
            message_line = next(
                line.strip()
                for line in response.split("\n")
                if line.strip().startswith("MESSAGE:")
            )
            message = message_line.replace("MESSAGE:", "").strip()

            # Validate message
            if not message:
                logger.warning("Empty message after parsing")
                return "..."  # Return a default message

            return message

        except Exception as e:
            logger.error(f"Error generating message: {str(e)}")
            return "..."  # Return a default message on error

    def _create_message_prompt(self, game_state: str) -> str:
        """Create prompt for message generation.

        Args:
            game_state: Current state of the game

        Returns:
            str: Formatted prompt for the LLM
        """
        return f"""
        You are a {self.communication_style} poker player.
        Current emotional state: {self.emotional_state}
        Game state: {game_state}
        Recent table history: {self.table_history[-3:] if self.table_history else 'None'}
        
        Generate a short, natural poker table message that:
        1. Fits your communication style ({self.communication_style})
        2. Responds to the current game state
        3. Maintains character consistency
        
        Respond with just the message in this format:
        MESSAGE: <your message here>
        """

    def perceive(self, game_state: str, opponent_message: Optional[str] = None) -> Dict:
        #! validate this
        #! this is how player gets a state for further processing
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

    def decide_discard(self, game_state: Optional[Dict[str, Any]] = None) -> List[int]:
        """Decide which cards to discard."""
        #! validate this
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
            response = self.llm_client.query(
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
            logger.error(f"Error in decide_draw: {str(e)}")
            return []

    def update_strategy(self, game_outcome: Dict[str, Any]) -> None:
        #! need to refactor and combine with strategy_planner (with strategy_manager)
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

        response = self.llm_client.query(prompt).strip()

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

    def analyze_opponent(self, opponent_name: str, game_state: str) -> Dict[str, Any]:
        #! validate and refactor this
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
            response = self.llm_client.query(prompt)
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
            logger.error(f"Error in opponent analysis: {str(e)}")
            return default_analysis
