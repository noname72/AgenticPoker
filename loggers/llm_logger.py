import logging
from typing import Optional, Union

logger = logging.getLogger(__name__)


class LLMLogger:
    """Handles all logging operations for LLM client interactions."""

    @staticmethod
    def log_query_error(error: Exception, context: str = "query") -> None:
        """Log errors during LLM queries."""
        logger.error(f"LLM {context} attempt failed: {str(error)}")

    @staticmethod
    def log_async_query_error(error: Exception) -> None:
        """Log errors during async LLM queries."""
        logger.error(f"Async LLM query failed: {str(error)}")

    @staticmethod
    def log_input_validation_error(param: str, value: Union[str, int, float]) -> None:
        """Log input validation errors."""
        logger.error(f"Invalid input parameter {param}: {value}")

    @staticmethod
    def log_retry_attempt(attempt: int, max_retries: int) -> None:
        """Log retry attempts."""
        logger.warning(f"Retry attempt {attempt}/{max_retries}")

    @staticmethod
    def log_metrics_update(
        duration: float,
        tokens: int,
        success: bool = True,
        error: Optional[Exception] = None,
    ) -> None:
        """Log metrics updates."""
        if success:
            logger.debug(
                f"Query completed - Duration: {duration:.2f}s, Tokens: {tokens}"
            )
        else:
            logger.warning(
                f"Query failed - Duration: {duration:.2f}s, Error: {str(error)}"
            )
