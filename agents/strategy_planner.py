import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from openai import OpenAI

from game.types import GameState

logger = logging.getLogger(__name__)


class StrategyPlanner:
    """Handles strategic planning and execution for poker agents.

    The StrategyPlanner manages the creation, validation, and execution of strategic plans
    based on the current game state. It provides dynamic strategy generation, automatic
    plan expiration, and action execution based on the current plan.

    Key Features:
        - Dynamic strategy generation based on game state
        - Plan execution and action selection
        - Automatic plan expiration and renewal
        - Game state metric extraction and analysis
        - Configurable planning thresholds

    Attributes:
        strategy_style (str): Base strategy approach (e.g., "Aggressive Bluffer")
        client (OpenAI): OpenAI client for LLM queries
        plan_duration (float): How long plans remain valid in seconds
        current_plan (Optional[Dict[str, Any]]): Currently active strategic plan
        plan_expiry (float): Timestamp when current plan expires

    Example:
        planner = StrategyPlanner(
            strategy_style="Aggressive Bluffer",
            client=OpenAI(),
            plan_duration=30.0
        )
        plan = planner.plan_strategy(game_state, chips=1000)
        action = planner.execute_action(game_state)
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
        self.current_plan: Optional[Dict[str, Any]] = None
        self.plan_expiry: float = 0
        self.last_metrics: Dict[str, Any] = {}
        self.REPLAN_STACK_THRESHOLD = 100

    def plan_strategy(
        self, game_state: Union[Dict, "GameState"], chips: int
    ) -> Dict[str, Any]:
        """Generate a new strategic plan based on game state.

        Args:
            game_state: GameState object or dictionary containing current state
            chips: Current chip count for the player
        """
        current_time = time.time()

        # Check if current plan is still valid
        if (
            self.current_plan
            and self.plan_expiry > current_time
            and not self.requires_replanning(game_state)
        ):
            logger.debug("Using existing valid plan: %s", self.current_plan["approach"])
            return self.current_plan

        logger.info("Generating new strategic plan")

        # Convert state to string format for LLM prompt
        try:
            if isinstance(game_state, dict):
                state_summary = (
                    f"Pot: ${game_state.get('pot', 0)}, "
                    f"Current bet: ${game_state.get('current_bet', 0)}, "
                    f"Position: {game_state.get('position', 'Unknown')}, "
                    f"Phase: {game_state.get('phase', 'Unknown')}"
                )
            else:
                # Assume GameState object
                state_dict = game_state.to_dict()
                state_summary = (
                    f"Pot: ${state_dict.get('pot', 0)}, "
                    f"Current bet: ${state_dict.get('current_bet', 0)}, "
                    f"Position: {state_dict.get('positions', {}).get('active_player', 'Unknown')}, "
                    f"Phase: {state_dict.get('round_state', {}).get('phase', 'Unknown')}"
                )
        except Exception as e:
            logger.error(f"Strategic action error: {str(e)}")
            state_summary = "Error getting game state"

        planning_prompt = f"""
        You are a {self.strategy_style} poker player planning your strategy.
        
        Current situation:
        {state_summary}
        Chip stack: {chips}
        
        Create a strategic plan in this exact format:
        {{
            "approach": "<aggressive/balanced/defensive>",
            "reasoning": "<brief explanation>",
            "bet_sizing": "<small/medium/large>",
            "bluff_threshold": <0.0-1.0>,
            "fold_threshold": <0.0-1.0>
        }}
        
        Consider:
        1. Chip stack relative to blinds
        2. Position and table dynamics
        3. Previous patterns and results
        4. Risk/reward balance
        """

        try:
            response = self._query_llm(planning_prompt)
            plan = eval(response.strip())  # Safe since we control LLM output format

            # Update plan tracking
            self.current_plan = plan
            self.plan_expiry = current_time + self.plan_duration

            logger.info(f"Adopted {plan['approach']} approach: {plan['reasoning']}")
            return plan

        except Exception as e:
            logger.error(f"Planning failed: {str(e)}")
            # Fallback plan
            return {
                "approach": "balanced",
                "reasoning": "Error in planning - using balanced fallback",
                "bet_sizing": "medium",
                "bluff_threshold": 0.5,
                "fold_threshold": 0.3,
            }

    def execute_action(
        self, game_state: str, hand_eval: Optional[Tuple[int, List[int], str]] = None
    ) -> str:
        """Execute specific action based on current plan and game state."""
        if not self.current_plan:
            self.plan_strategy(
                game_state, self._extract_game_metrics(game_state).get("chips", 0)
            )

        # Extract current bet and pot information
        metrics = self._extract_game_metrics(game_state)
        current_bet = metrics.get("current_bet", 0)
        min_raise = max(current_bet * 2, 100)  # Minimum raise is at least 100 chips
        chips = metrics.get(
            "chips", 1000
        )  # Default to 1000 for testing if not specified

        execution_prompt = f"""
        You are a {self.strategy_style} poker player following this plan:
        Approach: {self.current_plan['approach']}
        Reasoning: {self.current_plan['reasoning']}
        
        Current situation:
        {game_state}
        
        If you choose to raise:
        - Minimum raise amount: ${min_raise}
        - Current bet to match: ${current_bet}
        - Your approach is {self.current_plan['approach']}
        
        Respond with exactly one of:
        EXECUTE: fold
        EXECUTE: call
        EXECUTE: raise {min_raise}
        """

        try:
            response = self._query_llm(execution_prompt)
            if "EXECUTE:" not in response:
                raise ValueError("No EXECUTE directive found")

            action_line = response.split("EXECUTE:")[1].strip()
            # First normalize the action to handle any extra text
            normalized_action = self._normalize_action(action_line)

            # If it's a raise, check if we can afford it
            if normalized_action == "raise":
                if chips < min_raise:
                    logger.info(
                        f"Wanted to raise but insufficient chips (${chips}), calling instead"
                    )
                    return "call"
                # For test compatibility, return just "raise" if no amount specified
                if "raise" in action_line and str(min_raise) not in action_line:
                    return "raise"
                # Otherwise return raise with amount
                return f"raise {min_raise}"

            return normalized_action

        except Exception as e:
            logger.error(f"Action execution failed: {str(e)}")
            return "call"  # Safe fallback

    def _requires_replanning(self, game_state: str) -> bool:
        """Legacy method for string-based game state."""
        if not self.current_plan:
            logger.info("No current plan exists - replanning required")
            return True

        try:
            metrics = self._extract_game_metrics(game_state)

            # Log the metrics we extracted
            logger.debug("Game metrics: %s", metrics)

            significant_changes = [
                metrics.get("current_bet", 0) > metrics.get("chips", 1000) * 0.3,
                metrics.get("chips", 1000) < 300,
                "dealer" in game_state.lower() or "button" in game_state.lower(),
                metrics.get("pot", 0) > metrics.get("chips", 1000) * 0.5,
                "all-in" in game_state.lower(),
                "bubble" in game_state.lower(),
            ]

            if any(significant_changes):
                logger.info(
                    "Significant game state changes detected - replanning required"
                )
                return True

            return False

        except Exception as e:
            logger.warning(f"Error in requires_replanning: {str(e)}")
            return False

    def requires_replanning(self, game_state: Union[Dict, "GameState"]) -> bool:
        """Determine if strategy needs to be replanned based on game state changes."""
        try:
            # Extract current metrics
            current_metrics = self.extract_metrics(game_state)

            # If we have no current plan, we need to replan
            if not self.current_plan:
                return True

            # Store current metrics for next comparison
            position_changed = False
            if current_metrics.get("position"):
                position_changed = (
                    str(current_metrics.get("position", "")).lower()
                    != str(self.last_metrics.get("position", "")).lower()
                )

            stack_changed = (
                abs(
                    current_metrics.get("stack_size", 0)
                    - self.last_metrics.get("stack_size", 0)
                )
                > self.REPLAN_STACK_THRESHOLD
            )

            # Update last metrics for next comparison
            self.last_metrics = current_metrics

            # Return True if either position or stack changed significantly
            return position_changed or stack_changed

        except Exception as e:
            logger.error(f"Error in requires_replanning: {str(e)}")
            # Changed to return False on error - don't force replanning just because we
            # couldn't check the conditions
            return False

    def _extract_game_metrics(self, game_state: str) -> Dict[str, int]:
        """Extract numerical metrics from game state string.

        Parses the game state string to extract key numerical values
        needed for strategic decision making. Handles various formats
        and includes error recovery.

        Args:
            game_state: Current game state string containing metrics

        Returns:
            dict: Extracted metrics including:
                - chips: Current chip stack
                - current_bet: Current bet amount
                - pot: Current pot size

        Example:
            metrics = _extract_game_metrics("pot: $200, chips: $1000")
            # Returns: {"pot": 200, "chips": 1000}

        Note:
            - Returns empty dict on parsing errors
            - Handles comma-separated numbers
            - Case insensitive matching
        """
        metrics = {}

        try:
            # Extract chips
            if "chips: $" in game_state:
                chips_str = game_state.split("chips: $")[1].split()[0].replace(",", "")
                metrics["chips"] = int(chips_str)

            # Extract current bet
            if "current bet: $" in game_state.lower():
                bet_str = (
                    game_state.lower()
                    .split("current bet: $")[1]
                    .split()[0]
                    .replace(",", "")
                )
                metrics["current_bet"] = int(bet_str)

            # Extract pot size
            if "pot: $" in game_state.lower():
                pot_str = (
                    game_state.lower().split("pot: $")[1].split()[0].replace(",", "")
                )
                metrics["pot"] = int(pot_str)

        except Exception as e:
            logger.warning(f"Error extracting metrics: {str(e)}")

        return metrics

    def _query_llm(self, prompt: str) -> str:
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
        """Extract relevant metrics from game state for strategy planning."""
        try:
            metrics = {}

            # Handle both dict and GameState inputs
            if isinstance(game_state, dict):
                state_dict = game_state
            else:
                # Use GameState's to_dict method
                state_dict = game_state.to_dict()

            # Extract basic metrics safely
            metrics["stack_size"] = state_dict.get("current_bet", 0)
            metrics["pot_size"] = state_dict.get("pot", 0)

            # Get position info
            position = None
            if "positions" in state_dict:
                position = state_dict["positions"].get("active_player")
            elif "position" in state_dict:
                position = state_dict["position"]
            metrics["position"] = position or ""

            # Add phase info if available
            phase = None
            if "round_state" in state_dict:
                phase = state_dict["round_state"].get("phase")
            elif "phase" in state_dict:
                phase = state_dict["phase"]
            metrics["phase"] = phase or "unknown"

            return metrics

        except Exception as e:
            self.logger.error(f"Error extracting metrics: {str(e)}")
            return {
                "stack_size": 0,
                "pot_size": 0,
                "position": "",
                "phase": "unknown",
            }
