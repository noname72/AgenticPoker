import logging
import os
import time
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
        self.persist_dir = os.path.join(results_dir, "chroma_db")
        os.makedirs(self.persist_dir, exist_ok=True)

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
                    logger.error(f"Failed to initialize ChromaDB after {max_retries} attempts: {str(e)}")
                    raise
                time.sleep(1)  # Wait before retry

    def _initialize_client(self):
        """Initialize or reinitialize the ChromaDB client and collection."""
        settings = Settings(
            anonymized_telemetry=False,
            allow_reset=True,
            is_persistent=True
        )

        try:
            # Create persistent client
            self.client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=settings
            )

            try:
                # Try to get existing collection
                self.collection = self.client.get_collection(name=self.safe_name)
                logger.info(f"Using existing collection: {self.safe_name}")
                
                # Get the current highest ID to continue counting
                try:
                    results = self.collection.get()
                    if results and results["ids"]:
                        max_id = max(int(id.split('_')[1]) for id in results["ids"])
                        self.id_counter = max_id
                except Exception as e:
                    logger.warning(f"Could not determine max ID: {e}")
                
            except InvalidCollectionException:
                # Create new collection if it doesn't exist
                self.collection = self.client.create_collection(
                    name=self.safe_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new collection: {self.safe_name}")

        except Exception as e:
            logger.error(f"Failed to initialize collection {self.safe_name}: {str(e)}")
            raise

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

    def get_relevant_memories(self, query: str, k: int = 2) -> List[Dict[str, Any]]:
        """Get relevant memories based on query.
        
        Args:
            query: Search query string
            k: Maximum number of memories to return (default: 2)
            
        Returns:
            List[Dict[str, Any]]: List of relevant memories
        """
        try:
            # Get total count of memories
            total_memories = len(self.collection.get()['ids'])
            
            # Adjust k if it exceeds available memories
            k = min(k, total_memories)
            
            if k == 0:
                return []
            
            # Query with adjusted k
            results = self.collection.query(
                query_texts=[query],
                n_results=k
            )
            
            memories = []
            for i in range(len(results['ids'][0])):
                memories.append({
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i]
                })
            
            return memories
            
        except Exception as e:
            logger.error(f"Error retrieving memories: {str(e)}")
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
                    if "no such table" not in str(e):  # Ignore if table already gone
                        logger.error(f"Failed to clear memories: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to clear memories: {str(e)}")

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
                    if "Python is likely shutting down" not in str(e):
                        logger.warning(f"Error closing client: {str(e)}")

            logger.info(f"Closed ChromaDB connection for {self.safe_name}")
        except Exception as e:
            if "Python is likely shutting down" not in str(e):
                logger.error(f"Error closing ChromaDB connection: {str(e)}")
