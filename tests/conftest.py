import pytest
from unittest.mock import Mock, patch
from agents.agent import Agent
import os


@pytest.fixture(autouse=True)
def setup_logging():
    """Automatically disable logging for all tests."""
    import logging

    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


@pytest.fixture(autouse=True)
def mock_openai_key():
    """Mock OpenAI API key for all tests."""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
        yield


@pytest.fixture
def mock_memory_store():
    """Fixture to create a mock memory store."""

    class MockMemoryStore:
        def __init__(self):
            self.memories = []

        def add_memory(self, text, metadata):
            self.memories.append({"text": text, "metadata": metadata})

        def get_relevant_memories(self, query, k=3):
            return self.memories[:k]

        def clear(self):
            self.memories = []

        def close(self):
            pass

    return MockMemoryStore()


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables"""
    os.environ['PYTEST_RUNNING'] = 'true'
    yield
    os.environ.pop('PYTEST_RUNNING', None)
