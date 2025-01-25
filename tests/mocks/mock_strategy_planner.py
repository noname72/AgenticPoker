from typing import Optional
from unittest.mock import MagicMock

from data.types.plan import Approach, BetSizing, Plan
from game.evaluator import HandEvaluation

DEFAULT_PLAN_DURATION = 30.0
REPLAN_STACK_THRESHOLD = 100


class MockStrategyPlanner:
    """A mock implementation of the StrategyPlanner class for testing purposes.

    This mock provides the same interface as the real StrategyPlanner but with
    configurable behaviors for testing different planning scenarios.

    Attributes:
        strategy_style (str): The playing style used for planning (e.g., 'aggressive', 'conservative')
        plan_duration (float): Duration in seconds for which a plan remains valid
        REPLAN_STACK_THRESHOLD (int): Stack size change that triggers a replan
        current_plan (Optional[Plan]): The currently active strategic plan
        last_metrics (Optional[dict]): Last recorded game metrics used for planning

    Usage:
        # Basic initialization
        planner = MockStrategyPlanner(strategy_style="aggressive")

        # Configure specific plan
        planner.set_current_plan(
            approach=Approach.AGGRESSIVE,
            reasoning="Strong hand position",
            bet_sizing=BetSizing.LARGE
        )

        # Configure replanning behavior
        planner.set_replanning_required(True)

        # Use in tests
        planner.plan_strategy(player_mock, game_mock, hand_eval_mock)
        assert planner.current_plan.approach == Approach.AGGRESSIVE

        # Verify method calls
        planner.plan_strategy.assert_called_once()
        planner.requires_replanning.assert_called_with(game_mock, player_mock)

    Default Behaviors:
        - plan_strategy: Creates/updates plan based on configuration
        - requires_replanning: Returns configured value or False
        - current_plan: Returns configured plan or default conservative plan
    """

    def __init__(
        self,
        strategy_style: str = "balanced",
        plan_duration: float = DEFAULT_PLAN_DURATION,
        replan_threshold: int = REPLAN_STACK_THRESHOLD,
    ):
        """Initialize mock strategy planner with configurable parameters.

        Args:
            strategy_style (str): Playing style to use for planning (e.g., 'aggressive', 'conservative')
            plan_duration (float, optional): How long plans remain valid in seconds. Defaults to DEFAULT_PLAN_DURATION.
            replan_threshold (int, optional): Stack change threshold that triggers replanning.
                Defaults to REPLAN_STACK_THRESHOLD.
        """
        self.strategy_style = strategy_style
        self.plan_duration = plan_duration
        self.REPLAN_STACK_THRESHOLD = replan_threshold

        # Create mock methods
        self.plan_strategy = MagicMock()
        self.requires_replanning = MagicMock(return_value=False)

        # Set up default behaviors
        self.plan_strategy.side_effect = self._default_plan_strategy

        # Configuration state
        self.current_plan = None
        self.last_metrics = None  # Added to match real implementation
        self._should_replan = False
        self._plan_error = None

    def _default_plan_strategy(
        self,
        player,
        game,
        hand_eval: Optional[HandEvaluation] = None,
    ) -> None:
        """Generate or update the agent's strategic plan based on current game state.

        This method evaluates the current game situation and either generates a new plan
        or maintains the existing one based on replanning criteria.

        Args:
            player (Player): The player for whom to generate the strategy
            game (Game): Current game state including all relevant poker information
            hand_eval (Optional[HandEvaluation], optional): Pre-computed hand evaluation.
                Defaults to None.

        Raises:
            Exception: If plan generation fails, falls back to default plan
        """
        if self._plan_error:
            raise self._plan_error

        if not self.current_plan or self._should_replan:
            self.current_plan = self._create_default_plan()

    def set_current_plan(
        self,
        approach: Approach = Approach.BALANCED,
        reasoning: str = "Test reasoning",
        bet_sizing: BetSizing = BetSizing.MEDIUM,
        bluff_threshold: float = 0.5,
        fold_threshold: float = 0.3,
        adjustments: list = None,
        target_opponent: Optional[str] = None,
    ) -> None:
        """Configure the current plan for testing.

        Args:
            approach (Approach): Strategy approach (e.g., AGGRESSIVE, BALANCED)
            reasoning (str): Plan reasoning text
            bet_sizing (BetSizing): Betting size strategy (e.g., SMALL, MEDIUM, LARGE)
            bluff_threshold (float): Threshold for bluffing decisions (0.0-1.0)
            fold_threshold (float): Threshold for folding decisions (0.0-1.0)
            adjustments (list, optional): List of plan adjustments. Defaults to None.
            target_opponent (str, optional): Target opponent name. Defaults to None.
        """
        import time

        self.current_plan = Plan(
            approach=approach,
            reasoning=reasoning,
            bet_sizing=bet_sizing,
            bluff_threshold=bluff_threshold,
            fold_threshold=fold_threshold,
            expiry=time.time() + self.plan_duration,
            adjustments=adjustments or [],
            target_opponent=target_opponent,
        )
        self.plan_strategy.reset_mock()

    def set_replanning_required(self, required: bool = True) -> None:
        """Configure whether replanning is required for testing.

        This method configures both the internal state and the mock return value
        for requires_replanning().

        Args:
            required (bool, optional): Whether replanning should be required. Defaults to True.
        """
        self._should_replan = required
        self.requires_replanning.return_value = required

    def configure_for_test(
        self,
        current_plan: Optional[Plan] = None,
        should_replan: bool = False,
        raise_error: Optional[Exception] = None,
    ) -> None:
        """Configure multiple mock planner behaviors for testing.

        This is a convenience method that combines setting the current plan,
        replanning behavior, and error simulation in one call.

        Args:
            current_plan (Optional[Plan], optional): Plan object to set as current. Defaults to None.
            should_replan (bool, optional): Whether replanning should be required. Defaults to False.
            raise_error (Optional[Exception], optional): Exception to raise during planning. Defaults to None.
        """
        self.current_plan = current_plan
        self._should_replan = should_replan
        self._plan_error = raise_error
        self.requires_replanning.return_value = should_replan

    def _create_default_plan(self) -> Plan:
        """Create a default Plan object for testing.

        Returns:
            Plan: A balanced default plan with standard thresholds and settings:
                - Balanced approach
                - Medium bet sizing
                - 0.5 bluff threshold
                - 0.3 fold threshold
                - Default duration expiry
        """
        import time

        return Plan(
            approach=Approach.BALANCED,
            reasoning="Default fallback plan due to error",  # Updated to match real implementation
            bet_sizing=BetSizing.MEDIUM,
            bluff_threshold=0.5,
            fold_threshold=0.3,
            expiry=time.time() + DEFAULT_PLAN_DURATION,  # Updated to use constant
            adjustments=[],
            target_opponent=None,
        )

    def reset(self) -> None:
        """Reset the mock planner to its initial state.

        Resets:
            - current_plan to None
            - _should_replan to False
            - _plan_error to None
            - Clears all mock call history
        """
        self.current_plan = None
        self._should_replan = False
        self._plan_error = None
        self.plan_strategy.reset_mock()
        self.requires_replanning.reset_mock()

    def __str__(self) -> str:
        """Get a human-readable representation of the mock planner's current state.

        Returns:
            str: String containing the strategy style, current plan approach (if any),
                and whether replanning is required
        """
        plan_status = (
            f"{self.current_plan.approach.value}" if self.current_plan else "No plan"
        )
        return (
            f"MockStrategyPlanner: {self.strategy_style}, "
            f"Current plan: {plan_status}, "
            f"Replan required: {self._should_replan}"
        )
