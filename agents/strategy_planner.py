import logging
import time
from typing import TYPE_CHECKING, Optional

from data.types.metrics import GameMetrics, SidePotMetrics
from data.types.plan import Approach, BetSizing, Plan
from data.types.player_types import PlayerPosition
from game.evaluator import HandEvaluation
from game.utils import get_min_bet

from .llm_response_generator import LLMResponseGenerator

if TYPE_CHECKING:
    from game.game import Game
    from game.player import Player


logger = logging.getLogger(__name__)

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
        self.current_plan = None
        self.last_metrics = None

    def plan_strategy(
        self,
        player: "Player",
        game: "Game",
        hand_eval: Optional[HandEvaluation] = None,
        community_cards: Optional[list] = None,
    ) -> None:
        """Generate or update the agent's strategic plan based on current game state."""
        try:
            if self.current_plan and not self.requires_replanning(game, player):
                logger.info(
                    f"[Strategy] Reusing existing plan: {self.current_plan.approach}"
                )
                return  # Early return when reusing existing plan

            # Use the strategy generator to get new plan data
            plan_data = LLMResponseGenerator.generate_plan(
                player=player,
                game_state=game.get_state(),
                hand_eval=hand_eval,
                community_cards=community_cards,
            )
            self.current_plan = self._create_plan_from_response(plan_data)
            logger.info(
                f"[Strategy] New Plan: approach={self.current_plan.approach} "
                f"reasoning='{self.current_plan.reasoning}'"
            )

        except Exception as e:
            logger.error(f"Error generating plan: {str(e)}")
            self.current_plan = self._create_default_plan()

    def _create_default_plan(self) -> Plan:
        """Create a default Plan object when errors occur or no plan is available.

        Returns:
            Plan: A balanced default plan with standard thresholds and settings
        """
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

    def _create_plan_from_response(self, plan_data: dict) -> Plan:
        """Create a Plan object from LLM response data with validation.

        Args:
            plan_data (dict): Parsed response data from LLM

        Returns:
            Plan: A new plan object with validated fields
        """
        return Plan(
            approach=Approach(plan_data.get("approach", "balanced")),
            reasoning=plan_data.get("reasoning", "Default reasoning"),
            bet_sizing=BetSizing(plan_data.get("bet_sizing", "medium")),
            bluff_threshold=float(plan_data.get("bluff_threshold", 0.5)),
            fold_threshold=float(plan_data.get("fold_threshold", 0.3)),
            expiry=time.time() + DEFAULT_PLAN_DURATION,
            adjustments=[],
            target_opponent=None,
        )

    def requires_replanning(self, game: "Game", player: "Player") -> bool:
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

            return False

        except Exception as e:
            logger.error(
                "[Planning] Error checking replan conditions: %s. Keeping current plan.",
                str(e),
            )
            return False  # Safe fallback - keep current plan on error
