from typing import Optional
from unittest.mock import MagicMock

from data.types.plan import Approach, BetSizing, Plan
from game.evaluator import HandEvaluation


class MockStrategyPlanner:
    """A mock implementation of the StrategyPlanner class for testing purposes.

    This mock provides the same interface as the real StrategyPlanner but with
    configurable behaviors for testing different planning scenarios.

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
        plan_duration: float = 30.0,
        replan_threshold: int = 100,
    ):
        """Initialize mock strategy planner with configurable parameters."""
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
        self._should_replan = False
        self._plan_error = None

    def _default_plan_strategy(
        self,
        player,
        game,
        hand_eval: Optional[HandEvaluation] = None,
    ) -> None:
        """Default behavior for strategy planning."""
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
            approach: Strategy approach
            reasoning: Plan reasoning
            bet_sizing: Betting size strategy
            bluff_threshold: Threshold for bluffing
            fold_threshold: Threshold for folding
            adjustments: List of plan adjustments
            target_opponent: Target opponent name
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
        """Configure whether replanning is required.

        Args:
            required: Whether replanning should be required
        """
        self._should_replan = required
        self.requires_replanning.return_value = required

    def configure_for_test(
        self,
        current_plan: Optional[Plan] = None,
        should_replan: bool = False,
        raise_error: Optional[Exception] = None,
    ) -> None:
        """Configure the mock planner's behavior for testing.

        Args:
            current_plan: Optional Plan object to set
            should_replan: Whether replanning should be required
            raise_error: Optional exception to raise during planning
        """
        self.current_plan = current_plan
        self._should_replan = should_replan
        self._plan_error = raise_error
        self.requires_replanning.return_value = should_replan

    def _create_default_plan(self) -> Plan:
        """Create a default Plan object for testing."""
        import time

        return Plan(
            approach=Approach.BALANCED,
            reasoning="Default test plan",
            bet_sizing=BetSizing.MEDIUM,
            bluff_threshold=0.5,
            fold_threshold=0.3,
            expiry=time.time() + self.plan_duration,
            adjustments=[],
            target_opponent=None,
        )

    def reset(self) -> None:
        """Reset the mock planner to default state."""
        self.current_plan = None
        self._should_replan = False
        self._plan_error = None
        self.plan_strategy.reset_mock()
        self.requires_replanning.reset_mock()

    def __str__(self) -> str:
        """Get string representation of mock planner state."""
        plan_status = (
            f"{self.current_plan.approach.value}" if self.current_plan else "No plan"
        )
        return (
            f"MockStrategyPlanner: {self.strategy_style}, "
            f"Current plan: {plan_status}, "
            f"Replan required: {self._should_replan}"
        )
