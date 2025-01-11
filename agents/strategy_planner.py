import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from openai import OpenAI

from agents.prompts import ACTION_PROMPT, PLANNING_PROMPT
from data.types.action_response import ActionResponse, ActionType
from data.types.llm_responses import PlanResponse
from data.types.plan import Approach, BetSizing, Plan
from data.types.player_types import PlayerPosition
from game.evaluator import HandEvaluation

from .llm_client import LLMClient

if TYPE_CHECKING:
    from game.game import Game

logger = logging.getLogger(__name__)

DEFAULT_PLAN_DURATION = 30.0
REPLAN_STACK_THRESHOLD = 100


class StrategyPlanner:
    """Strategic planning and execution engine for poker agents.

    This class manages the complete strategic decision-making process for poker agents,
    including plan generation, validation, execution, and automatic renewal based on
    game conditions. It uses LLM-based decision making through an LLMClient for both
    strategy planning and action execution.

    Attributes:
        strategy_style (str): The playing style used for planning (e.g. aggressive, conservative)
        client (OpenAI): OpenAI client instance for LLM queries
        plan_duration (float): Duration in seconds that plans remain valid
        REPLAN_STACK_THRESHOLD (int): Stack size change that triggers replanning
        current_plan (Optional[Plan]): Currently active strategic plan
        last_metrics (Dict[str, Any]): Previously recorded game metrics
        llm_client (LLMClient): Client for LLM interactions
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
        self.last_metrics: Dict[str, Any] = {}
        self.llm_client = LLMClient(
            api_key=os.getenv("OPENAI_API_KEY"), model="gpt-3.5-turbo"
        )

    def execute_action(
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
                max_tokens=150,
            )
            logger.info(f"[Action Response] {action_response}")

            return self._parse_action_response(action_response, game)

        except Exception as e:
            logger.error(f"[Action] Error executing action: {str(e)}")
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

            min_bet = self.get_min_bet(game)

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
        #! validate this logic
        """Determine if current game state requires a new strategic plan."""
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
            current_metrics = self.extract_metrics(game)

            # Check for position change
            new_position = current_metrics.get("position", "").lower()
            old_position = self.last_metrics.get("position", "").lower()
            position_changed = new_position != old_position

            # Check for significant stack size change
            new_stack = current_metrics.get("stack_size", 0)
            old_stack = self.last_metrics.get("stack_size", 0)
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

    def extract_metrics(self, game: "Game") -> Dict[str, Any]:
        """Extract and normalize key metrics from the game state.

        Processes the current game state to extract relevant metrics for decision making
        and plan evaluation. Handles missing or invalid data gracefully.

        Args:
            game: Current game state object

        Returns:
            Dict[str, Any]: Normalized metrics including:
                - stack_size (int): Current player's chip count
                - pot_size (int): Current pot size
                - position (str): Player's position (dealer/small_blind/big_blind/etc)
                - phase (str): Current game phase
                - players_remaining (int): Number of active players
                - pot_odds (float): Ratio of current bet to pot size
                - stack_to_pot (float): Ratio of stack size to pot
                - relative_position (Optional[int]): Position relative to dealer (0=dealer)
                - min_bet (int): Minimum bet amount
                - current_bet (int): Current bet to call
                - side_pots (Optional[List[Dict]]): Information about side pots if any exist

        Raises:
            No direct exceptions - errors are caught and logged, returning default metrics
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

            # Calculate relative position (0 = dealer, 1 = SB, 2 = BB, etc)
            if active_position is not None:
                metrics["relative_position"] = (
                    active_position - game.dealer_position
                ) % len(game.players)
            else:
                metrics["relative_position"] = None

            # Add side pot information if any exists
            if game.pot_state.side_pots:
                metrics["side_pots"] = [
                    {
                        "amount": pot.amount,
                        "eligible_players": len(pot.eligible_players),
                    }
                    for pot in game.pot_state.side_pots
                ]

            return metrics

        except Exception as e:
            logger.error(f"Error extracting metrics: {str(e)}")
            # Return basic metrics as fallback
            return {
                "stack_size": 0,
                "pot_size": 0,
                "position": PlayerPosition.OTHER,
                "phase": "unknown",
                "players_remaining": 0,
                "pot_odds": 0.0,
                "stack_to_pot": 0.0,
                "relative_position": None,
                "min_bet": game.min_bet,
                "current_bet": 0,
            }

    def _format_state_summary(self, game: "Game") -> str:
        """Format game state into a string summary.

        Args:
            game_state: Current game state as GameState object

        Returns:
            str: Formatted summary of game state
        """
        try:
            return (
                f"Pot: ${game.pot_manager.pot}, "
                f"Current bet: ${getattr(game.round_state, 'current_bet', 0)}, "
                f"Phase: {game.round_state.phase}"
            )
        except Exception as e:
            logger.error(f"Error formatting game state: {str(e)}")
            raise

    def _get_position_name(
        self, active_position: Optional[int], num_players: int, dealer_position: int
    ) -> str:
        """Get the position name relative to the dealer.

        Converts numeric positions to meaningful poker position names based on the
        number of players and dealer position.

        Args:
            active_position: Current active player's position (0-based index)
            num_players: Total number of players in the game
            dealer_position: Dealer's position (0-based index)

        Returns:
            str: Position name (dealer/small_blind/big_blind/under_the_gun/middle/cutoff)
                Returns 'unknown' if position cannot be determined

        Raises:
            No direct exceptions - errors are caught and logged, returning 'unknown'
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

    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate LLM response into plan data.

        Args:
            response: Raw response string from LLM containing JSON plan data

        Returns:
            Dict[str, Any]: Validated plan data with fields:
                - approach (str): Strategic approach (default: 'balanced')
                - reasoning (str): Plan justification
                - bet_sizing (str): Bet sizing strategy (default: 'medium')
                - bluff_threshold (float): Threshold for bluffing (default: 0.5)
                - fold_threshold (float): Threshold for folding (default: 0.3)
        """
        return PlanResponse.parse_llm_response(response)

    def get_min_bet(self, game: "Game") -> int:
        """Calculate the minimum allowed bet amount.

        Args:
            game: Current game state

        Returns:
            int: Minimum allowed bet amount
        """
        # If no current bet, use big blind as minimum
        if game.current_bet == 0:
            return game.big_blind

        # For raises, minimum is double the current bet
        return game.current_bet * 2
