import logging
import os
import time
from typing import TYPE_CHECKING, Optional

from agents.prompts import ACTION_PROMPT, PLANNING_PROMPT
from data.types.action_response import ActionResponse, ActionType
from data.types.llm_responses import PlanResponse
from data.types.metrics import GameMetrics, SidePotMetrics
from data.types.plan import Approach, BetSizing, Plan
from data.types.player_types import PlayerPosition
from game.evaluator import HandEvaluation
from game.utils import get_min_bet

#! query through player instead
from .llm_client import LLMClient

if TYPE_CHECKING:
    from game.game import Game

logger = logging.getLogger(__name__)

#! move to config
DEFAULT_PLAN_DURATION = 30.0
REPLAN_STACK_THRESHOLD = 100


class StrategyPlanner:
    """Strategic planning and execution engine for poker agents.

    This class manages the complete strategic decision-making process for poker agents,
    including plan generation, validation, execution, and automatic renewal based on
    game conditions. It uses LLM-based decision making through an LLMClient for both
    strategy planning and action execution.
    """

    def __init__(
        self,
        strategy_style: str,
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
        self.plan_duration = plan_duration
        self.REPLAN_STACK_THRESHOLD = replan_threshold
        self.current_plan: Optional[Plan] = None
        self.last_metrics: Optional[GameMetrics] = None
        self.llm_client = LLMClient(
            api_key=os.getenv("OPENAI_API_KEY"), model="gpt-3.5-turbo"
        )

    def get_action(
        self,
        game: "Game",
        hand_eval: Optional[HandEvaluation] = None,
    ) -> ActionResponse:
        """Execute an action based on current plan and game state.

        Generates and executes a poker action (call, fold, raise) based on the current
        strategic plan and game state. Creates a new plan if none exists.

        Args:
            game: Current game state containing pot, player positions, and betting info
            hand_eval: Optional evaluation of the current hand strength

        Returns:
            ActionResponse: The action to take
                Defaults to 'call' if errors occur during execution

        Raises:
            No direct exceptions - errors are caught and logged, returning 'call'
        """
        try:
            # Ensure we have a valid plan
            if not self.current_plan:
                logger.info(
                    "[Action] No active plan - generating new plan before action"
                )
                self.plan_strategy(game, hand_eval)

            # Create execution prompt
            execution_prompt = ACTION_PROMPT.format(
                strategy_style=self.strategy_style,
                game_state=game.get_state(),  #! prob passing too much info
                hand_eval=hand_eval,
                plan_approach=self.current_plan.approach,
                plan_reasoning=self.current_plan.reasoning,
                bluff_threshold=self.current_plan.bluff_threshold,
                fold_threshold=self.current_plan.fold_threshold,
            )

            # Get response from LLM
            action_response = self.llm_client.query(
                prompt=execution_prompt,
                temperature=0.7,
                max_tokens=100,
            )

            return self._parse_action_response(action_response, game)

        except Exception as e:
            logger.error(
                f"[Action] Error executing action: {str(e)}, defaulting to call"
            )
            return ActionResponse(action_type=ActionType.CALL)

    def plan_strategy(
        self,
        game: "Game",
        hand_eval: Optional[HandEvaluation] = None,
    ) -> Plan:
        """Generate or update the agent's strategic plan based on current game state.

        This method evaluates the current game state and hand evaluation to create a new
        strategic plan or validate/reuse an existing one. It uses LLM to generate plans
        that include approach, bet sizing, and various thresholds.

        Args:
            game: Current game state containing pot, player positions, and betting info
            hand_eval: Optional evaluation of the current hand strength

        Returns:
            Plan: A strategic plan object containing approach, bet sizing, and thresholds.
                Returns default balanced plan if errors occur during generation.

        Raises:
            No direct exceptions - errors are caught and logged, returning default plan
        """
        try:
            # Check if current plan is still valid
            if self.current_plan and not self.requires_replanning(game):
                logger.info(
                    f"[Strategy] Reusing existing plan: {self.current_plan.approach}"
                )
                return self.current_plan

            # Create planning prompt using the constant
            prompt = PLANNING_PROMPT.format(
                strategy_style=self.strategy_style,
                game_state=game.get_state(),
                hand_eval=hand_eval,
            )

            # Query LLM for plan
            response = self.llm_client.query(
                prompt=prompt, temperature=0.7, max_tokens=200
            )

            plan_data = PlanResponse.parse_llm_response(response)

            # Create new plan with proper validation
            self.current_plan = Plan(
                approach=Approach(plan_data.get("approach", "balanced")),
                reasoning=plan_data.get("reasoning", "Default reasoning"),
                bet_sizing=BetSizing(plan_data.get("bet_sizing", "medium")),
                bluff_threshold=float(plan_data.get("bluff_threshold", 0.5)),
                fold_threshold=float(plan_data.get("fold_threshold", 0.3)),
                expiry=time.time() + DEFAULT_PLAN_DURATION,
                adjustments=[],
                target_opponent=None,
            )

            logger.info(
                f"[Strategy] New Plan: approach={self.current_plan.approach} "
                f"reasoning='{self.current_plan.reasoning}'"
            )

            return self.current_plan

        except Exception as e:
            logger.error(f"Error generating plan: {str(e)}")
            # Create and return a default plan instead of failing
            return Plan(
                approach=Approach.BALANCED,
                reasoning="Default fallback plan due to error",
                bet_sizing=BetSizing.MEDIUM,
                bluff_threshold=0.5,
                fold_threshold=0.3,
                expiry=time.time() + DEFAULT_PLAN_DURATION,
                adjustments=[],
                target_opponent=None,
            )

    def _parse_action_response(self, response: str, game: "Game") -> ActionResponse:
        """Parse the LLM response and return the appropriate action.

        Args:
            response: Raw response string from LLM
            game: Current game state

        Returns:
            ActionResponse: The action to take
        """
        try:
            action = ActionResponse.parse_llm_response(response)

            min_bet = get_min_bet(game)

            # Validate raise amount against game rules
            if action.action_type == ActionType.RAISE:

                if action.raise_amount < min_bet:
                    logger.info(
                        f"[Action] Raise {action.raise_amount} below minimum {min_bet}, converting to call"
                    )
                    action.raise_amount = min_bet

            logger.info(f"[Action] {action}")
            return action

        except Exception as e:
            logger.error(f"[Action] Error parsing action response: {str(e)}")
            return "call"

    def requires_replanning(self, game: "Game") -> bool:
        """Determine if current game state requires a new strategic plan.

        Evaluates several conditions to decide if a new strategic plan is needed:
        1. No current plan exists
        2. Current plan has expired based on time
        3. Player position has changed
        4. Significant stack size change (beyond REPLAN_STACK_THRESHOLD)

        Args:
            game: Current game state containing player positions, stack sizes,
                 and other relevant game information

        Returns:
            bool: True if replanning is required, False if current plan remains valid

        Note:
            - Position changes always trigger replanning to adapt strategy
            - Stack size changes only trigger replanning if they exceed REPLAN_STACK_THRESHOLD
            - Game metrics are only updated if no replanning is required
            - On error, defaults to False to keep current plan as safe fallback
        """
        # Always replan if no current plan exists
        if not self.current_plan:
            logger.debug("[Planning] No current plan exists - replanning required")
            return True

        try:
            # Check if plan has expired
            if self.current_plan.is_expired():
                logger.debug(
                    "[Planning] Current plan has expired - replanning required"
                )
                return True

            # Extract current metrics using unified method
            current_metrics: GameMetrics = self.extract_metrics(game)

            # Check for position change
            new_position = current_metrics.position
            old_position = self.last_metrics.position
            position_changed = new_position != old_position

            # Check for significant stack size change
            new_stack = current_metrics.stack_size
            old_stack = self.last_metrics.stack_size
            stack_changed = abs(new_stack - old_stack) > self.REPLAN_STACK_THRESHOLD

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

            needs_replanning = position_changed or stack_changed

            # Only update metrics if we're not replanning
            if not needs_replanning:
                self.last_metrics = current_metrics

            return needs_replanning

        except Exception as e:
            logger.error(
                "[Planning] Error checking replan conditions: %s. Keeping current plan.",
                str(e),
            )
            return False  # Safe fallback - keep current plan on error

    def extract_metrics(self, game: "Game") -> GameMetrics:
        """Extract and normalize key metrics from the game state.

        Processes the current game state to extract relevant metrics for decision making
        and plan evaluation. Handles missing or invalid data gracefully.

        Args:
            game: Current game state object

        Returns:
            GameMetrics: Normalized metrics including stack sizes, positions, and derived calculations

        Note:
            Returns default metrics with zero values if errors occur during extraction
        """
        try:
            # Find the active player's state
            active_player_state = None
            active_position = game.active_player_position
            if active_position is not None:
                active_player_state = game.players[active_position]

            # Extract basic metrics
            metrics = {
                "stack_size": active_player_state.chips if active_player_state else 0,
                "pot_size": game.pot_state.main_pot,
                "position": (
                    active_player_state.position.value
                    if active_player_state
                    else PlayerPosition.OTHER
                ),
                "phase": game.round_state.phase,
                "players_remaining": len([p for p in game.players if not p.folded]),
                "min_bet": game.min_bet,
                "current_bet": getattr(game.round_state, "current_bet", 0),
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

            # Calculate relative position
            if active_position is not None:
                metrics["relative_position"] = (
                    active_position - game.dealer_position
                ) % len(game.players)

            # Add side pot information if any exists
            if game.pot_state.side_pots:
                metrics["side_pots"] = [
                    SidePotMetrics(
                        amount=pot.amount, eligible_players=len(pot.eligible_players)
                    )
                    for pot in game.pot_state.side_pots
                ]

            return GameMetrics(**metrics)

        except Exception as e:
            logger.error(f"Error extracting metrics: {str(e)}")
            # Return basic metrics as fallback
            return GameMetrics(
                stack_size=0,
                pot_size=0,
                position=PlayerPosition.OTHER.value,
                phase="unknown",
                players_remaining=0,
                pot_odds=0.0,
                stack_to_pot=0.0,
                min_bet=game.min_bet,
                current_bet=0,
            )
