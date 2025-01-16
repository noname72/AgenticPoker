import logging
from typing import Optional

from data.types.action_response import ActionResponse

logger = logging.getLogger(__name__)


class AgentLogger:
    """Handles all logging operations for poker agents."""

    @staticmethod
    def log_action(action: ActionResponse, error: Optional[Exception] = None) -> None:
        """Log agent actions or action-related errors."""
        if error:
            logger.error(
                f"[Action] Error executing action: {str(error)}, defaulting to call"
            )
        else:
            logger.info(f"[Action] {action}")

    @staticmethod
    def log_message_generation(error: Optional[Exception] = None) -> None:
        """Log message generation events or errors."""
        if error:
            logger.error(f"Error generating message: {str(error)}")
        else:
            logger.warning("No MESSAGE: found in response")

    @staticmethod
    def log_strategy_update(
        agent_name: str, old_strategy: str, new_strategy: str
    ) -> None:
        """Log strategy changes."""
        logger.info(
            "[Strategy Update] %s changing strategy from %s to %s",
            agent_name,
            old_strategy,
            new_strategy,
        )

    @staticmethod
    def log_opponent_analysis_error(error: Exception) -> None:
        """Log errors during opponent analysis."""
        logger.error(f"Error in opponent analysis: {str(error)}")

    @staticmethod
    def log_discard_error(error: Exception) -> None:
        """Log errors during discard decisions."""
        logger.error(f"Error in decide_draw: {str(error)}")

    @staticmethod
    def log_cleanup_error(error: Exception, context: str) -> None:
        """Log cleanup-related errors."""
        if "Python is likely shutting down" not in str(error):
            logger.warning(f"Error cleaning up {context}: {str(error)}")

    @staticmethod
    def log_general_cleanup_error(error: Exception) -> None:
        """Log general cleanup errors."""
        if "Python is likely shutting down" not in str(error):
            logger.error(f"Error in cleanup: {str(error)}")
