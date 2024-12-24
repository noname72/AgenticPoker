import logging
import time
from typing import Any, Dict, Optional

from openai import OpenAI

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

    def plan_strategy(self, game_state: str, chips: int) -> Dict[str, Any]:
        """Generate a new strategic plan based on game state.

        Creates a short-term strategic plan considering the agent's traits, current
        game state, and chip stack. Plans include approach, bet sizing, and
        thresholds for actions.

        Args:
            game_state: Current game situation including pot size, position, etc.
            chips: Current chip count for the player

        Returns:
            dict: Strategic plan containing:
                - approach: Overall strategy (aggressive/defensive/balanced)
                - reasoning: Explanation of the chosen approach
                - bet_sizing: Preferred bet size (small/medium/large)
                - bluff_threshold: Probability threshold for bluffing (0.0-1.0)
                - fold_threshold: Probability threshold for folding (0.0-1.0)

        Example Plan:
            {
                "approach": "aggressive",
                "reasoning": "Strong hand, weak opponents",
                "bet_sizing": "large",
                "bluff_threshold": 0.7,
                "fold_threshold": 0.2
            }

        Note:
            - Plans expire after plan_duration seconds
            - Returns fallback balanced plan on errors
            - Considers position and table dynamics
        """
        current_time = time.time()

        # Check if current plan is still valid
        if (
            self.current_plan
            and self.plan_expiry > current_time
            and not self._requires_replanning(game_state)
        ):
            logger.debug("Using existing valid plan: %s", self.current_plan["approach"])
            return self.current_plan

        logger.info("Generating new strategic plan")
        planning_prompt = f"""
        You are a {self.strategy_style} poker player planning your strategy.
        
        Current situation:
        {game_state}
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
                "reasoning": "Error in planning, falling back to balanced approach",
                "bet_sizing": "medium",
                "bluff_threshold": 0.5,
                "fold_threshold": 0.3,
            }

    def execute_action(self, game_state: str) -> str:
        """Execute specific action based on current plan and game state.

        Translates strategic plan into concrete poker action considering
        current situation and plan parameters. Uses LLM to evaluate the
        situation against the current plan's thresholds and approach.

        Args:
            game_state: Current game situation including pot size, position, etc.

        Returns:
            str: Concrete action ('fold', 'call', or 'raise')

        Note:
            - Falls back to 'call' if execution fails
            - Considers bluff and fold thresholds from plan
            - Evaluates pot odds and immediate costs
            - Validates action matches strategic approach

        Example:
            planner.execute_action("pot: $200, current_bet: $50...")
            # Returns: "raise"
        """
        if not self.current_plan:
            return "call"  # Safe default if no plan exists

        execution_prompt = f"""
        You are a {self.strategy_style} poker player following this plan:
        Approach: {self.current_plan['approach']}
        Reasoning: {self.current_plan['reasoning']}
        
        Current situation:
        {game_state}
        
        Given your {self.current_plan['approach']} approach:
        1. Evaluate if the situation matches your plan
        2. Consider pot odds and immediate action costs
        3. Factor in your bluff_threshold ({self.current_plan['bluff_threshold']}) and fold_threshold ({self.current_plan['fold_threshold']})
        
        Respond with EXECUTE: <fold/call/raise> and brief reasoning
        """

        try:
            response = self._query_llm(execution_prompt)
            if "EXECUTE:" not in response:
                raise ValueError("No EXECUTE directive found")

            action = response.split("EXECUTE:")[1].strip().split()[0]
            return self._normalize_action(action)

        except Exception as e:
            logger.error(f"Execution failed: {str(e)}")
            return "call"  # Safe fallback

    def _requires_replanning(self, game_state: str) -> bool:
        """Determine if current situation requires a new plan.

        Evaluates game state changes to decide if current strategic plan
        remains valid or needs updating. Considers multiple factors to
        trigger replanning.

        Args:
            game_state: Current game state string containing situation details

        Returns:
            bool: True if replanning needed, False otherwise

        Triggers:
            - Missing current plan
            - Significant bet sizes (>30% of stack)
            - Low chip stack (<300)
            - Position changes to late position
            - Large pot relative to stack (>50%)
            - All-in situations
            - Tournament bubble situations

        Note:
            Returns False on error to maintain current plan
        """
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

        Processes and standardizes action strings from LLM responses into
        valid poker actions. Handles variations and embedded actions.

        Args:
            action: Raw action string from LLM

        Returns:
            str: Normalized action ('fold', 'call', or 'raise')

        Note:
            - Strips whitespace and converts to lowercase
            - Returns 'call' as safe default for invalid actions
            - Handles only the three valid poker actions
        """
        action = action.lower().strip()
        if action in ["fold", "call", "raise"]:
            return action
        return "call"  # Safe default
