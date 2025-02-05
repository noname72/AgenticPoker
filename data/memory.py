import os
import shutil
import tempfile
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union

import chromadb
from chromadb.config import Settings
from chromadb.errors import InvalidCollectionException

from loggers.memory_logger import MemoryLogger

try:
    # Python 3.10+ type annotation
    QueryType = str | Dict
except TypeError:
    # Fallback for older Python versions
    QueryType = Union[str, Dict]


class MemoryStore(ABC):
    """Abstract base class for memory storage implementations.

    This class defines the interface for storing and retrieving memories
    with associated metadata. Concrete implementations must provide specific
    storage solutions.
    """

    @abstractmethod
    def add_memory(self, text: str, metadata: Dict[str, Any]) -> None:
        """Store a new memory with associated metadata.

        Args:
            text: The text content of the memory to store
            metadata: Dictionary containing additional information about the memory
        """
        pass

    @abstractmethod
    def get_relevant_memories(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve k most relevant memories for a given query.

        Args:
            query: The search query text
            k: Maximum number of memories to return (default: 3)

        Returns:
            List of dictionaries containing memory text and metadata
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored memories."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close any open connections."""
        pass


class ChromaMemoryStore(MemoryStore):
    """Chroma-based implementation of memory storage.

    This class implements persistent memory storage using ChromaDB as the backend.
    Memories are stored with embeddings for semantic search capabilities.

    Args:
        collection_name: Name of the ChromaDB collection to use
    """

    def __init__(self, collection_name: str):
        # Add environment check at the start
        os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Prevent warning messages

        # Use temporary directory for tests
        if os.environ.get("PYTEST_RUNNING"):
            temp_dir = tempfile.gettempdir()
            self.persist_dir = os.path.join(temp_dir, "chroma_test_db")
        else:
            results_dir = os.path.join(os.getcwd(), "results")
            self.persist_dir = os.path.join(results_dir, "chroma_db")

        # Clean up existing directory if in test mode
        if os.environ.get("PYTEST_RUNNING"):
            try:
                if os.path.exists(self.persist_dir):
                    shutil.rmtree(self.persist_dir)
                    time.sleep(0.2)  # Give OS time to release handles
            except PermissionError:
                MemoryLogger.log_cleanup_warning(self.persist_dir)
                # Try to clean up contents instead
                for item in os.listdir(self.persist_dir):
                    try:
                        path = os.path.join(self.persist_dir, item)
                        if os.path.isfile(path):
                            os.unlink(path)
                        elif os.path.isdir(path):
                            shutil.rmtree(path)
                    except Exception as e:
                        MemoryLogger.log_cleanup_item_error(path, e)

        # Create directory
        try:
            os.makedirs(self.persist_dir, exist_ok=True)
        except Exception as e:
            MemoryLogger.log_init_error(e, self.persist_dir)
            raise

        # Sanitize collection name and ensure uniqueness
        self.safe_name = "".join(c for c in collection_name if c.isalnum() or c in "_-")
        self.id_counter = 0

        # Initialize client with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._initialize_client()
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    MemoryLogger.log_chroma_init_error(e)
                    raise
                time.sleep(1)  # Wait before retry

    def _initialize_client(self):
        """Initialize or reinitialize the ChromaDB client and collection."""
        try:
            # Create persistent client with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Use new client initialization style
                    self.client = chromadb.Client(
                        chromadb.config.Settings(
                            is_persistent=True,
                            persist_directory=self.persist_dir,
                            anonymized_telemetry=False,
                        )
                    )
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(0.5)

            # Add retry logic for collection initialization
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Try to get existing collection
                    self.collection = self.client.get_collection(name=self.safe_name)
                    MemoryLogger.log_collection_status(self.safe_name)

                    # Verify collection is working
                    try:
                        self.collection.count()
                    except Exception:
                        MemoryLogger.log_collection_warning(
                            "Collection exists but may be corrupted, recreating..."
                        )
                        self.client.delete_collection(name=self.safe_name)
                        raise InvalidCollectionException()

                except InvalidCollectionException:
                    # Create new collection if it doesn't exist or is corrupted
                    self.collection = self.client.create_collection(
                        name=self.safe_name, metadata={"hnsw:space": "cosine"}
                    )
                    MemoryLogger.log_collection_status(self.safe_name, is_new=True)
                    break

                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(0.5)  # Wait before retry

            # Get the current highest ID to continue counting
            try:
                results = self.collection.get()
                if results and results["ids"]:
                    max_id = max(int(id.split("_")[1]) for id in results["ids"])
                    self.id_counter = max_id
            except Exception as e:
                MemoryLogger.log_max_id_error(e)
                self.id_counter = 0

        except Exception as e:
            MemoryLogger.log_chroma_init_error(e)
            raise

    def add_memory(self, text: str, metadata: Dict[str, Any]) -> None:
        """Store a new memory in Chroma with improved error handling."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if not self.collection:
                    self._initialize_client()

                # Add unique timestamp to metadata
                metadata = {**metadata, "timestamp": time.time()}

                self.id_counter += 1
                mem_id = f"mem_{self.id_counter}"

                # Add with retries
                retry_count = 0
                while retry_count < 3:
                    try:
                        self.collection.add(
                            documents=[text], metadatas=[metadata], ids=[mem_id]
                        )
                        time.sleep(0.1)  # Small delay to ensure processing
                        break
                    except Exception as e:
                        retry_count += 1
                        if retry_count == 3:
                            raise
                        time.sleep(0.2)
                break

            except Exception as e:
                if attempt == max_retries - 1:
                    MemoryLogger.log_memory_add_error(e, max_retries)
                    raise
                time.sleep(0.5)

    def get_relevant_memories(
        self, query: Union[str, Dict], k: int = 2
    ) -> List[Dict[str, Any]]:
        """Get relevant memories based on query."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.collection is None:
                    MemoryLogger.log_collection_reinit()
                    self._initialize_client()

                # Handle dictionary queries by converting to string
                if isinstance(query, dict):
                    query = str(query)  # Convert dict to string representation

                # Get total count of memories
                total_memories = len(self.collection.get()["ids"])

                # Adjust k if it exceeds available memories
                k = min(k, total_memories)

                if k == 0:
                    return []

                # Query with adjusted k
                results = self.collection.query(
                    query_texts=[query],
                    n_results=k,
                    include=["documents", "metadatas"],  # Explicitly request all data
                )

                # Check if we got valid results
                if not results or not results["ids"][0]:
                    MemoryLogger.log_query_warning(query)
                    return []

                memories = []
                for i in range(len(results["ids"][0])):
                    memories.append(
                        {
                            "text": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i],
                        }
                    )

                return memories

            except (InvalidCollectionException, AttributeError) as e:
                MemoryLogger.log_collection_error(e, attempt)
                if attempt < max_retries - 1:
                    self._initialize_client()
                    time.sleep(0.2)  # Give time for initialization
                else:
                    MemoryLogger.log_collection_recovery_error()
                    return []

            except Exception as e:
                MemoryLogger.log_memory_retrieval_error(e)
                return []

    def clear(self) -> None:
        """Clear all memories from the collection."""
        try:
            if hasattr(self, "collection") and self.collection:
                try:
                    # Get all document IDs first
                    results = self.collection.get()
                    if results and results["ids"]:
                        # Delete all documents by ID
                        self.collection.delete(ids=results["ids"])
                    self.id_counter = 0
                except Exception as e:
                    MemoryLogger.log_clear_error(e)
        except Exception as e:
            MemoryLogger.log_clear_error(e)

    def close(self) -> None:
        """Close the Chroma client connection and cleanup resources."""
        try:
            if hasattr(self, "collection"):
                self.collection = None

            if hasattr(self, "client"):
                try:
                    # Don't reset the client on close to maintain persistence
                    self.client = None
                except Exception as e:
                    MemoryLogger.log_client_warning(e)

            MemoryLogger.log_connection_close(self.safe_name)
        except Exception as e:
            MemoryLogger.log_close_error(e)
