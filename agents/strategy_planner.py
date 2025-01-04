import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from openai import OpenAI

from game.types import GameState

from .llm_client import LLMClient
from .types import Approach, BetSizing, Plan

logger = logging.getLogger(__name__)


class StrategyPlanner:
    """Strategic planning and execution engine for poker agents.

    This class manages the complete strategic decision-making process for poker agents,
    including plan generation, validation, execution, and automatic renewal based on
    game conditions. It uses LLM-based decision making through an LLMClient for both
    strategy planning and action execution.

    The planner uses a combination of:
    - LLM-based strategy generation and action decisions
    - Dynamic plan adjustment based on game state
    - Automatic plan expiration and renewal
    - Metric-based strategy validation
    - Fallback strategies for error handling

    Key Features:
        - Dynamic strategy generation based on current game state
        - Automatic plan expiration and renewal system
        - Position and stack-based replanning triggers
        - Robust error handling with fallback strategies
        - Configurable planning thresholds and durations
        - LLM-powered decision making

    Attributes:
        strategy_style (str): Base strategy style (e.g., "Aggressive", "Conservative")
        client (OpenAI): OpenAI client instance for LLM queries
        plan_duration (float): Duration in seconds before plans expire
        current_plan (Optional[Plan]): Currently active strategic plan
        plan_expiry (float): Unix timestamp when current plan expires
        last_metrics (Dict[str, Any]): Previously extracted game metrics
        REPLAN_STACK_THRESHOLD (int): Stack change threshold that triggers replanning
        llm_client (LLMClient): Client handling all LLM-based decision making

    Example:
        >>> client = OpenAI()
        >>> planner = StrategyPlanner(
        ...     strategy_style="Aggressive",
        ...     client=client,
        ...     plan_duration=30.0
        ... )
        >>> game_state = {"pot": 100, "position": "dealer", "phase": "preflop"}
        >>> plan = planner.plan_strategy(game_state, chips=1000)
        >>> action = planner.execute_action(game_state)
        >>> print(f"Decided action: {action}")  # e.g. "raise 200"

    Notes:
        - Uses fallback to balanced strategy on planning errors
        - Defaults to 'call' action on execution errors
        - Automatically replans on position changes or significant stack changes
        - Validates all plans through Pydantic models
    """

    def __init__(
        self, strategy_style: str, client: OpenAI, plan_duration: float = 30.0
    ) -> None:
        """Initialize the strategy planner.

        Args:
            strategy_style: Playing style to use for planning
            client: OpenAI client for LLM queries
            plan_duration: How long plans remain valid (seconds)
        """
        self.strategy_style = strategy_style
        self.client = client
        self.plan_duration = plan_duration
        self.current_plan: Optional[Plan] = None
        self.plan_expiry: float = 0
        self.last_metrics: Dict[str, Any] = {}
        self.REPLAN_STACK_THRESHOLD = 100
        self.llm_client = LLMClient(client)

    def plan_strategy(self, game_state: Union[Dict, "GameState"], chips: int) -> Plan:
        """Generate or retrieve a strategic plan based on current game state.

        This method either returns the current valid plan or generates a new one if:
        - No current plan exists
        - Current plan has expired
        - Game state changes require replanning

        Args:
            game_state: Current game state either as a dict or GameState object
            chips: Current chip count for the player

        Returns:
            Plan: A valid strategic plan containing approach, bet sizing, and thresholds

        Raises:
            None: Uses fallback plan on errors instead of raising exceptions

        Notes:
            - Plans include approach, bet sizing, bluff/fold thresholds
            - Plans automatically expire after plan_duration seconds
            - Fallback to balanced strategy on planning failures
        """
        current_time = time.time()

        # Check if current plan is still valid
        if (
            self.current_plan
            and not self.current_plan.is_expired(current_time)
            and not self.requires_replanning(game_state)
        ):
            logger.debug(
                "[Strategy] Using existing valid plan '%s' (expires in %.1f seconds)",
                self.current_plan.approach.value,
                self.current_plan.expiry - current_time,
            )
            return self.current_plan

        logger.info("[Strategy] Initiating new strategic plan generation")

        try:
            # Extract metrics using unified method
            metrics = self.extract_metrics(game_state)
            logger.debug("[Strategy] Extracted metrics: %s", metrics)

            # Use LLMClient to generate plan
            plan_dict = self.llm_client.generate_plan(
                strategy_style=self.strategy_style,
                game_state=self._format_state_summary(metrics),
            )

            # Use Pydantic model for validation
            plan = Plan(**plan_dict, expiry=current_time + self.plan_duration)

            # Update plan tracking
            self.current_plan = plan

            logger.info(
                "[Strategy] Successfully adopted %s approach: %s",
                plan.approach.value,
                plan.reasoning,
            )
            return plan

        except Exception as e:
            logger.error(
                "[Strategy] Failed to generate new plan: %s. Using fallback balanced plan.",
                str(e),
            )
            # Fallback plan
            return Plan(
                approach=Approach.BALANCED,
                reasoning="Error in planning - using balanced fallback",
                bet_sizing=BetSizing.MEDIUM,
                bluff_threshold=0.5,
                fold_threshold=0.3,
                expiry=current_time + self.plan_duration,
                adjustments=[],
                target_opponent=None,
            )

    def execute_action(
        self, game_state: str, hand_eval: Optional[Tuple[int, List[int], str]] = None
    ) -> str:
        """Execute an action based on current plan and game state.

        Determines the optimal action to take based on:
        - Current strategic plan
        - Game state
        - Optional hand evaluation data

        Args:
            game_state: Current game state as a string
            hand_eval: Optional tuple of (hand_rank, card_ranks, hand_name)

        Returns:
            str: Action to take ('fold', 'call', 'raise', or 'raise X')

        Notes:
            - Generates new plan if none exists
            - Uses LLM for action decision making
            - Falls back to 'call' on execution errors
            - Logs decision reasoning and errors
        """
        if not self.current_plan:
            logger.info("[Action] No active plan - generating new plan before action")
            self.plan_strategy(
                game_state, self.extract_metrics(game_state).get("stack_size", 0)
            )

        try:
            # Use LLMClient to get action
            action = self.llm_client.decide_action(
                strategy_style=self.strategy_style,
                game_state=game_state,
                plan=self.current_plan.dict(),
            )

            logger.info(
                "[Action] Decided on '%s' based on %s strategy",
                action,
                self.current_plan.approach.value,
            )
            return action

        except Exception as e:
            logger.error(
                "[Action] Failed to execute action: %s. Defaulting to 'call'", str(e)
            )
            return "call"  # Safe fallback

    def requires_replanning(self, game_state: Union[Dict, "GameState"]) -> bool:
        """Determine if current game state requires a new strategic plan.

        Evaluates multiple factors to decide if replanning is needed:
        - Position changes
        - Significant stack size changes
        - Plan expiration
        - Missing current plan

        Args:
            game_state: Current game state as dict or GameState object

        Returns:
            bool: True if replanning is required, False otherwise

        Notes:
            - Compares current metrics against last recorded metrics
            - Uses REPLAN_STACK_THRESHOLD for stack change evaluation
            - Logs significant changes that trigger replanning
            - Returns False on evaluation errors to maintain current plan
        """
        # Always replan if no current plan exists
        if not self.current_plan:
            logger.debug("[Planning] No current plan exists - replanning required")
            return True

        try:
            # Extract current metrics using unified method
            current_metrics = self.extract_metrics(game_state)

            # Check for position change
            new_position = current_metrics.get("position", "").lower()
            old_position = self.last_metrics.get("position", "").lower()
            position_changed = new_position != old_position

            # Check for significant stack size change
            new_stack = current_metrics.get("stack_size", 0)
            old_stack = self.last_metrics.get("stack_size", 0)
            stack_changed = abs(new_stack - old_stack) > self.REPLAN_STACK_THRESHOLD

            # Store current metrics for next comparison
            self.last_metrics = current_metrics

            # Log significant changes
            if position_changed:
                logger.info(
                    "[Planning] Position changed from '%s' to '%s' - replanning needed",
                    old_position,
                    new_position,
                )
            if stack_changed:
                logger.info(
                    "[Planning] Stack changed by %d chips (threshold: %d) - replanning needed",
                    abs(new_stack - old_stack),
                    self.REPLAN_STACK_THRESHOLD,
                )

            return position_changed or stack_changed

        except Exception as e:
            logger.error(
                "[Planning] Error checking replan conditions: %s. Keeping current plan.",
                str(e),
            )
            return False  # Safe fallback - keep current plan on error

    def _query_llm(self, prompt: str) -> str:
        #! keep this in client
        """Send query to LLM and get response.

        Handles communication with the OpenAI API, including error handling
        and response validation.

        Args:
            prompt: Formatted prompt string for the LLM

        Returns:
            str: LLM's response text

        Raises:
            Exception: If LLM query fails or returns invalid response

        Note:
            - Uses GPT-4 model by default
            - Sets temperature=0.7 for some variability
            - Raises exceptions rather than returning fallbacks
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM query failed: {str(e)}")
            raise

    def _normalize_action(self, action: str) -> str:
        #! is this needed???
        """Normalize action string to valid poker action.

        Args:
            action: Raw action string from LLM response

        Returns:
            str: Normalized action ('fold', 'call', 'raise', or 'raise X')

        Examples:
            >>> _normalize_action("fold because weak hand")
            'fold'
            >>> _normalize_action("raise with strong hand")
            'raise'
            >>> _normalize_action("raise 200")
            'raise 200'
        """
        action = action.lower().strip()

        # First check for exact matches
        if action in ["fold", "call", "raise"]:
            return action

        # Handle raise amounts (e.g., "raise 200")
        if action.startswith("raise "):
            try:
                # Try to extract raise amount
                _, amount = action.split(maxsplit=1)
                if amount.isdigit():
                    return f"raise {amount}"
            except (ValueError, IndexError):
                pass
            # If we couldn't extract a valid amount, return just "raise"
            return "raise"

        # Extract basic action word if embedded in a phrase
        if "fold" in action:
            return "fold"
        if "raise" in action:
            return "raise"
        if "call" in action or "check" in action:
            return "call"

        return "call"  # Safe default

    def extract_metrics(self, game_state: Union[Dict, "GameState"]) -> Dict[str, Any]:
        """Extract and normalize key metrics from the game state.

        Processes raw game state into standardized metrics used for strategy decisions.
        Handles both dictionary and GameState object inputs.

        Args:
            game_state: Current game state as dict or GameState object

        Returns:
            Dict[str, Any]: Normalized metrics including:
                - stack_size: Current stack size
                - pot_size: Current pot size
                - position: Player's position
                - phase: Game phase
                - current_bet: Current bet amount
                - is_preflop: Boolean for preflop phase
                - is_late_position: Boolean for late position

        Notes:
            - Handles missing data gracefully
            - Returns safe defaults on extraction errors
            - Normalizes position and phase names
            - Adds derived metrics for common checks
        """
        try:
            # Convert GameState to dictionary if needed
            if not isinstance(game_state, dict):
                state_dict = game_state.to_dict()
            else:
                state_dict = game_state

            metrics = {
                "stack_size": state_dict.get("current_bet", 0),
                "pot_size": state_dict.get("pot", 0),
                "current_bet": state_dict.get("current_bet", 0),
            }

            # Extract position with consistent format
            if "positions" in state_dict:
                metrics["position"] = state_dict["positions"].get("active_player", "")
            elif "position" in state_dict:
                metrics["position"] = state_dict["position"]
            else:
                metrics["position"] = ""

            # Extract phase with consistent format
            if "round_state" in state_dict:
                metrics["phase"] = state_dict["round_state"].get("phase", "unknown")
            elif "phase" in state_dict:
                metrics["phase"] = state_dict["phase"]
            else:
                metrics["phase"] = "unknown"

            # Add derived metrics
            metrics["is_preflop"] = metrics["phase"].lower() == "preflop"
            metrics["is_late_position"] = metrics["position"].lower() in [
                "dealer",
                "cutoff",
            ]

            logger.debug("[Metrics] Successfully extracted game metrics: %s", metrics)
            return metrics

        except Exception as e:
            logger.error(
                "[Metrics] Failed to extract metrics: %s. Using safe defaults.", str(e)
            )
            return {
                "stack_size": 0,
                "pot_size": 0,
                "position": "",
                "phase": "unknown",
                "current_bet": 0,
                "is_preflop": False,
                "is_late_position": False,
            }

    def _format_state_summary(self, game_state: Union[Dict, "GameState"]) -> str:
        """Format game state into a string summary.

        Args:
            game_state: Current game state as dict or GameState object

        Returns:
            str: Formatted summary of game state
        """
        try:
            if isinstance(game_state, dict):
                state_dict = game_state
            else:
                # Assume GameState object
                state_dict = game_state.to_dict()

            return (
                f"Pot: ${state_dict.get('pot', 0)}, "
                f"Current bet: ${state_dict.get('current_bet', 0)}, "
                f"Position: {state_dict.get('positions', {}).get('active_player', 'Unknown')}, "
                f"Phase: {state_dict.get('round_state', {}).get('phase', 'Unknown')}"
            )
        except Exception as e:
            logger.error(f"Error formatting game state: {str(e)}")
            return str(game_state)
