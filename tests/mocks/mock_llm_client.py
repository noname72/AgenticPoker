from typing import Any, Dict, Optional, Union
from unittest.mock import MagicMock

from exceptions import LLMError


class MockLLMClient:
    """A mock implementation of the LLMClient class for testing purposes.

    This mock provides the same interface as the real LLMClient but with configurable
    behaviors for testing. It allows easy configuration of responses, errors, and metrics
    tracking for testing different scenarios.

    Usage:
        # Basic initialization
        client = MockLLMClient()

        # Configure specific responses
        client.set_response("Test prompt", "Expected response")

        # Configure error scenarios
        client.configure_for_test(should_raise_error=True)

        # Configure metrics
        client.configure_metrics(
            total_queries=10,
            failed_queries=2,
            total_tokens=1000
        )

        # Test async behavior
        client.set_async_response("Test prompt", "Async response")

        # Verify method calls
        client.query.assert_called_with("Test prompt", temperature=0.7)
        client.query_async.assert_called_once()

    Default Behaviors:
        - query: Returns configured response or raises configured error
        - query_async: Returns configured async response or raises error
        - get_metrics: Returns configured metrics
        - reset_metrics: Resets metrics to default values

    Attributes:
        metrics (Dict): Tracks usage metrics
        model (str): Model identifier
        max_retries (int): Maximum retry attempts
    """

    def __init__(
        self,
        api_key: str = "mock_key",
        model: str = "gpt-3.5-turbo",
        max_retries: int = 3,
    ):
        """Initialize mock LLM client with configurable parameters."""
        self.model = model
        self.max_retries = max_retries

        # Initialize metrics
        self.metrics = {
            "total_queries": 0,
            "failed_queries": 0,
            "retry_count": 0,
            "total_tokens": 0,
            "query_times": [],
        }

        # Create mock methods
        self.query = MagicMock()
        self.query_async = MagicMock()
        self.get_metrics = MagicMock()
        self.reset_metrics = MagicMock()

        # Set up default behaviors
        self.query.side_effect = self._default_query
        self.query_async.side_effect = self._default_query_async
        self.get_metrics.side_effect = self._default_get_metrics
        self.reset_metrics.side_effect = self._default_reset_metrics

        # Response configuration
        self._responses = {}
        self._async_responses = {}
        self._should_raise_error = False
        self._error_message = "Mock LLM Error"

    def _default_query(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
        system_message: Optional[str] = None,
    ) -> str:
        """Default behavior for synchronous query."""
        if self._should_raise_error:
            self.metrics["failed_queries"] += 1
            raise LLMError(self._error_message)

        self.metrics["total_queries"] += 1
        self.metrics["total_tokens"] += 50  # Mock token count
        self.metrics["query_times"].append(0.1)  # Mock query time

        return self._responses.get(prompt, "Default mock response")

    async def _default_query_async(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
        system_message: Optional[str] = None,
    ) -> str:
        """Default behavior for asynchronous query."""
        if self._should_raise_error:
            self.metrics["failed_queries"] += 1
            raise LLMError(self._error_message)

        self.metrics["total_queries"] += 1
        self.metrics["total_tokens"] += 50
        self.metrics["query_times"].append(0.1)

        return self._async_responses.get(prompt, "Default mock async response")

    def _default_get_metrics(self) -> Dict[str, Union[int, float, list]]:
        """Default behavior for getting metrics."""
        metrics = self.metrics.copy()
        if self.metrics["query_times"]:
            metrics["average_query_time"] = sum(self.metrics["query_times"]) / len(
                self.metrics["query_times"]
            )
        return metrics

    def _default_reset_metrics(self) -> None:
        """Default behavior for resetting metrics."""
        self.metrics = {
            "total_queries": 0,
            "failed_queries": 0,
            "retry_count": 0,
            "total_tokens": 0,
            "query_times": [],
        }

    def set_response(self, prompt: str, response: str) -> None:
        """Configure response for a specific prompt.

        Args:
            prompt: The input prompt
            response: The desired response
        """
        self._responses[prompt] = response
        self.query.reset_mock()

    def set_async_response(self, prompt: str, response: str) -> None:
        """Configure async response for a specific prompt.

        Args:
            prompt: The input prompt
            response: The desired async response
        """
        self._async_responses[prompt] = response
        self.query_async.reset_mock()

    def configure_for_test(
        self,
        should_raise_error: bool = False,
        error_message: Optional[str] = None,
    ) -> None:
        """Configure the mock client's behavior for testing.

        Args:
            should_raise_error: Whether queries should raise errors
            error_message: Custom error message when raising errors
        """
        self._should_raise_error = should_raise_error
        if error_message:
            self._error_message = error_message

    def configure_metrics(
        self,
        total_queries: int = 0,
        failed_queries: int = 0,
        retry_count: int = 0,
        total_tokens: int = 0,
        query_times: Optional[list] = None,
    ) -> None:
        """Configure metrics for testing.

        Args:
            total_queries: Total number of queries
            failed_queries: Number of failed queries
            retry_count: Number of retries
            total_tokens: Total tokens used
            query_times: List of query durations
        """
        self.metrics = {
            "total_queries": total_queries,
            "failed_queries": failed_queries,
            "retry_count": retry_count,
            "total_tokens": total_tokens,
            "query_times": query_times or [],
        }

    def __str__(self) -> str:
        """Get string representation of mock client state."""
        return (
            f"MockLLMClient: {self.metrics['total_queries']} queries, "
            f"{self.metrics['failed_queries']} failed, "
            f"{self.metrics['total_tokens']} tokens used"
        )
