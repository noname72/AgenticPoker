import logging
from typing import Optional, Union
import time

logger = logging.getLogger("loggers.llm_logger")


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

    @staticmethod
    def log_prompt_and_response(
        prompt: str,
        response: str,
        system_message: Optional[str] = None,
        model: str = "unknown",
        tags: Optional[str] = None,
    ) -> None:
        """Log the prompt sent to and response received from the LLM.

        Args:
            prompt: The prompt sent to the LLM
            response: The response received from the LLM
            system_message: Optional system message included with the prompt
            model: The LLM model used
            tags: Optional tags to identify the interaction
        """
        separator = "=" * 50
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        log_message = f"\n{separator}\n"
        log_message += f"LLM Interaction - {timestamp}\n"
        log_message += f"Model: {model}\n"
        if tags:
            log_message += f"Tags: {tags}\n"
        log_message += f"{separator}\n"

        if system_message:
            log_message += f"SYSTEM MESSAGE:\n{system_message}\n\n"

        log_message += f"PROMPT:\n{prompt}\n\n"
        log_message += f"RESPONSE:\n{response}\n"
        log_message += f"{separator}\n"

        logger.debug(log_message)
