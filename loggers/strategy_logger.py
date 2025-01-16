import logging

from data.types.plan import Plan

logger = logging.getLogger(__name__)


class StrategyLogger:
    """Handles all logging operations for strategy planning."""

    @staticmethod
    def log_plan_reuse(plan: Plan) -> None:
        """Log when an existing plan is being reused."""
        logger.info(f"[Strategy] Reusing existing plan: {plan.approach}")

    @staticmethod
    def log_new_plan(plan: Plan) -> None:
        """Log when a new plan is created."""
        logger.info(
            f"[Strategy] New Plan: approach={plan.approach} "
            f"reasoning='{plan.reasoning}'"
        )

    @staticmethod
    def log_plan_error(error: Exception) -> None:
        """Log errors during plan generation."""
        logger.error(f"Error generating plan: {str(error)}")

    @staticmethod
    def log_planning_check(reason: str) -> None:
        """Log planning check results."""
        logger.debug(f"[Planning] {reason}")

    @staticmethod
    def log_replan_error(error: Exception) -> None:
        """Log errors during replan checking."""
        logger.error(
            "[Planning] Error checking replan conditions: %s. Keeping current plan.",
            str(error),
        )
