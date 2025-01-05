import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from openai import OpenAI

from game.types import GameState

from .llm_client import LLMClient
from .types import Approach, BetSizing, Plan

logger = logging.getLogger(__name__)

DEFAULT_PLAN_DURATION = 30.0
REPLAN_STACK_THRESHOLD = 100
DEFAULT_TEMPERATURE = 0.7


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
        self,
        strategy_style: str,
        client: OpenAI,
        plan_duration: float = DEFAULT_PLAN_DURATION,
        replan_threshold: int = REPLAN_STACK_THRESHOLD,
    ) -> None:
        """Initialize the strategy planner.

        Args:
            strategy_style: Playing style to use for planning
            client: OpenAI client for LLM queries
            plan_duration: How long plans remain valid (seconds)
            replan_threshold: Stack change threshold that triggers replanning
        """
        self.strategy_style = strategy_style
        self.client = client
        self.plan_duration = plan_duration
        self.REPLAN_STACK_THRESHOLD = replan_threshold
        self.current_plan: Optional[Plan] = None
        self.last_metrics: Dict[str, Any] = {}
        self.llm_client = LLMClient(client)

    def plan_strategy(self, game_state: "GameState", chips: int) -> Plan:
        """Generate or retrieve a strategic plan based on current game state.

        Args:
            game_state: Current game state as GameState object
            chips: Current chip count for the player

        Returns:
            Plan: A valid strategic plan
        """
        current_time = time.time()

        try:
            # Check if current plan is still valid
            if (
                self.current_plan
                and not self.current_plan.is_expired(current_time)
                and not self.requires_replanning(game_state)
            ):
                logger.debug(
                    "[Strategy] Using existing plan '%s' (expires in %.1f seconds)",
                    self.current_plan.approach.value,
                    self.current_plan.expiry - current_time,
                )
                return self.current_plan

            # Extract metrics first to validate game state
            metrics = self.extract_metrics(game_state)

            # Create fallback plan if no position found
            if not metrics["position"]:
                logger.warning("[Strategy] No position found - using fallback plan")
                fallback_plan = Plan(
                    approach=Approach.BALANCED,
                    reasoning="No position information available - using balanced approach",
                    bet_sizing=BetSizing.MEDIUM,
                    bluff_threshold=0.5,
                    fold_threshold=0.3,
                    expiry=current_time + self.plan_duration,
                    adjustments=[],
                    target_opponent=None,
                )
                self.current_plan = fallback_plan
                return fallback_plan

            logger.info(
                "[Strategy] Generating new plan for position: %s", metrics["position"]
            )

            # Generate new plan
            plan_dict = self.llm_client.generate_plan(
                strategy_style=self.strategy_style,
                game_state=self._format_state_summary(game_state),
            )

            # Validate and create plan
            plan = Plan(**plan_dict, expiry=current_time + self.plan_duration)
            self.current_plan = plan

            logger.info(
                "[Strategy] Created new %s plan: %s",
                plan.approach.value,
                plan.reasoning,
            )
            return plan

        except Exception as e:
            logger.error("[Strategy] Plan generation failed: %s", str(e))
            # Fallback plan
            fallback_plan = Plan(
                approach=Approach.BALANCED,
                reasoning=f"Error in planning: {str(e)}",
                bet_sizing=BetSizing.MEDIUM,
                bluff_threshold=0.5,
                fold_threshold=0.3,
                expiry=current_time + self.plan_duration,
                adjustments=[],
                target_opponent=None,
            )
            self.current_plan = fallback_plan
            return fallback_plan

    def execute_action(
        self,
        game_state: "GameState",
        hand_eval: Optional[Tuple[int, List[int], str]] = None,
    ) -> str:
        """Execute an action based on current plan and game state.

        Args:
            game_state: Current game state as GameState object
            hand_eval: Tuple of (hand_rank, card_ranks, hand_name) representing hand strength

        Returns:
            str: Action to take ('fold', 'call', 'raise', or 'raise X')
        """
        try:
            # Ensure we have a valid plan
            if not self.current_plan:
                logger.info(
                    "[Action] No active plan - generating new plan before action"
                )
                self.plan_strategy(
                    game_state, self.extract_metrics(game_state).get("stack_size", 0)
                )

            # Ensure we still have a valid plan after attempting to generate one
            if not self.current_plan:
                logger.warning(
                    "[Action] Failed to generate plan - using default action"
                )
                return "call"

            # Pass hand_eval to LLMClient for better decision making
            action = self.llm_client.decide_action(
                strategy_style=self.strategy_style,
                game_state=self._format_state_summary(game_state),
                plan=self.current_plan.dict(),
                hand_eval=hand_eval,
            )

            logger.info(
                "[Action] Decided on '%s' based on %s strategy with hand %s",
                action,
                self.current_plan.approach.value,
                hand_eval[2] if hand_eval else "unknown",
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

    def extract_metrics(self, game_state: "GameState") -> Dict[str, Any]:
        """Extract and normalize key metrics from the game state.

        Args:
            game_state: Current game state as GameState object

        Returns:
            Dict[str, Any]: Normalized metrics including:
                - stack_size: Current player's chip count
                - pot_size: Current pot size
                - position: Player's position (dealer/small_blind/big_blind/etc)
                - phase: Current game phase
                - players_remaining: Number of active players
                - pot_odds: Ratio of current bet to pot size
                - stack_to_pot: Ratio of stack size to pot
                - relative_position: Position relative to dealer (0=dealer)
                - min_bet: Minimum bet amount
                - current_bet: Current bet to call
        """
        try:
            # Find the active player's state
            active_player_state = None
            active_position = game_state.active_player_position
            if active_position is not None:
                active_player_state = game_state.players[active_position]

            # Extract basic metrics
            metrics = {
                "stack_size": active_player_state.chips if active_player_state else 0,
                "pot_size": game_state.pot_state.main_pot,
                "position": (
                    active_player_state.position.value if active_player_state else None
                ),
                "phase": game_state.round_state.phase,
                "players_remaining": len(
                    [p for p in game_state.players if not p.folded]
                ),
                "min_bet": game_state.min_bet,
                "current_bet": getattr(game_state.round_state, "current_bet", 0),
            }

            # Calculate derived metrics
            if metrics["current_bet"] > 0 and metrics["pot_size"] > 0:
                metrics["pot_odds"] = metrics["current_bet"] / metrics["pot_size"]
            else:
                metrics["pot_odds"] = 0.0

            if metrics["pot_size"] > 0:
                metrics["stack_to_pot"] = metrics["stack_size"] / metrics["pot_size"]
            else:
                metrics["stack_to_pot"] = float("inf")

            # Calculate relative position (0 = dealer, 1 = SB, 2 = BB, etc)
            if active_position is not None:
                metrics["relative_position"] = (
                    active_position - game_state.dealer_position
                ) % len(game_state.players)
            else:
                metrics["relative_position"] = None

            # Add side pot information if any exists
            if game_state.pot_state.side_pots:
                metrics["side_pots"] = [
                    {
                        "amount": pot.amount,
                        "eligible_players": len(pot.eligible_players),
                    }
                    for pot in game_state.pot_state.side_pots
                ]

            return metrics

        except Exception as e:
            logger.error(f"Error extracting metrics: {str(e)}")
            # Return basic metrics as fallback
            return {
                "stack_size": 0,
                "pot_size": 0,
                "position": None,
                "phase": "unknown",
                "players_remaining": 0,
                "pot_odds": 0.0,
                "stack_to_pot": 0.0,
                "relative_position": None,
                "min_bet": game_state.min_bet,
                "current_bet": 0,
            }

    def _format_state_summary(self, game_state: "GameState") -> str:
        """Format game state into a string summary.

        Args:
            game_state: Current game state as GameState object

        Returns:
            str: Formatted summary of game state
        """
        try:
            return (
                f"Pot: ${game_state.pot_state.main_pot}, "
                f"Current bet: ${getattr(game_state.round_state, 'current_bet', 0)}, "
                f"Position: {self._get_position_name(game_state.active_player_position, len(game_state.players), game_state.dealer_position)}, "
                f"Phase: {game_state.round_state.phase}"
            )
        except Exception as e:
            logger.error(f"Error formatting game state: {str(e)}")
            raise

    def _get_position_name(
        self, active_position: Optional[int], num_players: int, dealer_position: int
    ) -> str:
        """Get the position name relative to the dealer.

        Args:
            active_position: Current active player's position (0-based index)
            num_players: Total number of players
            dealer_position: Dealer's position (0-based index)

        Returns:
            str: Position name (dealer/small_blind/big_blind/under_the_gun/middle/cutoff)
        """
        try:
            if active_position is None:
                return "unknown"

            # Calculate relative position from dealer (0 = dealer, 1 = SB, 2 = BB, etc)
            relative_pos = (active_position - dealer_position) % num_players

            # Map relative positions to names
            position_names = {
                0: "dealer",
                1: "small_blind",
                2: "big_blind",
                3: "under_the_gun",
            }

            # Special case for cutoff (second to last to act)
            if relative_pos == num_players - 1:
                return "cutoff"

            # Return mapped position or "middle" for other positions
            return position_names.get(relative_pos, "middle")

        except Exception as e:
            logger.error(f"Error determining position name: {str(e)}")
            return "unknown"
