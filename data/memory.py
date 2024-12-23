import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import chromadb
from chromadb.config import Settings
from chromadb.errors import InvalidCollectionException

logger = logging.getLogger(__name__)


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
        # Ensure results directory exists
        results_dir = os.path.join(os.getcwd(), "results")
        persist_dir = os.path.join(results_dir, "chroma_db")
        os.makedirs(persist_dir, exist_ok=True)

        # Sanitize collection name
        self.safe_name = "".join(c for c in collection_name if c.isalnum() or c in "_-")
        self.persist_dir = persist_dir
        self.id_counter = 0

        self._initialize_client()

    def _initialize_client(self):
        """Initialize or reinitialize the ChromaDB client and collection."""
        try:
            self.client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(
                    anonymized_telemetry=False, allow_reset=True, is_persistent=True
                ),
            )

            # Get or create collection
            try:
                self.collection = self.client.get_collection(name=self.safe_name)
                logger.info(f"Using existing collection: {self.safe_name}")
            except InvalidCollectionException:
                self.collection = self.client.create_collection(
                    name=self.safe_name, metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new collection: {self.safe_name}")

        except Exception as e:
            logger.error(f"Failed to initialize collection {self.safe_name}: {str(e)}")
            # Create in-memory fallback
            self.client = chromadb.Client(Settings(anonymized_telemetry=False))
            self.collection = self.client.create_collection(
                name=self.safe_name, metadata={"hnsw:space": "cosine"}
            )
            logger.warning("Falling back to in-memory storage")

    def add_memory(self, text: str, metadata: Dict[str, Any]) -> None:
        """Store a new memory in Chroma.

        Args:
            text: The text content to store
            metadata: Dictionary of metadata associated with the memory

        Note:
            If the collection becomes invalid, it will attempt to reinitialize
            and retry the operation.
        """
        try:
            self.id_counter += 1
            self.collection.add(
                documents=[text], metadatas=[metadata], ids=[f"mem_{self.id_counter}"]
            )
        except InvalidCollectionException:
            logger.warning("Collection lost, reinitializing...")
            self._initialize_client()
            # Retry the add operation
            self.collection.add(
                documents=[text], metadatas=[metadata], ids=[f"mem_{self.id_counter}"]
            )
        except Exception as e:
            logger.error(f"Failed to add memory: {str(e)}")

    def get_relevant_memories(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Query Chroma for relevant memories.

        Args:
            query: The search query text
            k: Maximum number of memories to return (default: 3)

        Returns:
            List of dictionaries containing:
                - text: The memory content
                - metadata: Associated metadata dictionary

        Note:
            Returns an empty list if the collection is invalid or query fails.
        """
        try:
            results = self.collection.query(query_texts=[query], n_results=k)

            memories = []
            if results and results["metadatas"]:
                for doc, metadata in zip(
                    results["documents"][0], results["metadatas"][0]
                ):
                    memories.append({"text": doc, "metadata": metadata})
            return memories
        except InvalidCollectionException:
            logger.warning("Collection lost, reinitializing...")
            self._initialize_client()
            # Return empty list after reinitialization since old memories are lost
            return []
        except Exception as e:
            logger.error(f"Failed to query memories: {str(e)}")
            return []

    def clear(self) -> None:
        """Clear all memories from the collection."""
        try:
            self.collection.delete()
            self._initialize_client()
            self.id_counter = 0
        except Exception as e:
            logger.error(f"Failed to clear memories: {str(e)}")

    def close(self) -> None:
        """Close the Chroma client connection."""
        try:
            if hasattr(self, "collection") and self.collection:
                try:
                    self.client.delete_collection(self.collection.name)
                except:
                    pass
                self.collection = None

            if hasattr(self, "client") and self.client:
                try:
                    self.client.reset()
                except:
                    pass
                self.client = None

            logger.info("Closed ChromaDB connection")
        except Exception as e:
            logger.error(f"Error closing ChromaDB connection: {str(e)}")
