# Memory Module Documentation

The memory module provides a flexible and persistent memory storage system for AI agents, allowing them to maintain context and learn from past interactions.

## Overview

The memory system uses vector embeddings to store and retrieve relevant memories, enabling agents to:
- Maintain context across multiple interactions
- Learn from past experiences
- Make more informed decisions based on historical data
- Persist memories between sessions

## Components

### MemoryStore (Abstract Base Class)

The base interface for all memory storage implementations, defining the core operations:

```python
class MemoryStore(ABC):
    def add_memory(self, text: str, metadata: Dict[str, Any]) -> None:
        """Store a new memory with metadata."""
        pass

    def get_relevant_memories(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve k most relevant memories for a query."""
        pass

    def clear(self) -> None:
        """Clear all stored memories."""
        pass
```

### ChromaMemoryStore

The default implementation using Chroma DB for vector storage:

- Persists memories to disk in `results/chroma_db/`
- Uses cosine similarity for memory retrieval
- Provides fallback to in-memory storage if persistence fails
- Handles collection management automatically

## Usage

### Basic Usage

```python
from data.memory import ChromaMemoryStore

# Initialize memory store
memory = ChromaMemoryStore("agent_alice")

# Store a memory
memory.add_memory(
    text="Opponent raised aggressively pre-flop",
    metadata={
        "type": "observation",
        "timestamp": time.time(),
        "strategy_style": "cautious"
    }
)

# Retrieve relevant memories
memories = memory.get_relevant_memories(
    query="aggressive betting patterns",
    k=3  # Get top 3 most relevant memories
)

# Clear all memories
memory.clear()
```

### Memory DTOs

The module includes data transfer objects for structured memory operations:

```python
class MemoryDTO(BaseModel):
    text: str
    metadata: Dict[str, Any]
    timestamp: datetime

class MemoryQueryDTO(BaseModel):
    query: str
    k: int = 3
    filters: Optional[Dict[str, Any]] = None
```

## Storage Details

Memories are stored in the following structure:
- Location: `results/chroma_db/`
- Format: Vector embeddings with metadata
- Persistence: Automatic with fallback to in-memory
- Collection naming: Sanitized agent names (e.g., "agent_alice_memory")

## Error Handling

The module includes comprehensive error handling:
- Graceful fallback to in-memory storage if persistence fails
- Automatic collection creation/recovery
- Logging of all errors and operations
- Safe collection name sanitization

## Best Practices

1. Memory Storage:
   - Store concise, relevant information
   - Include meaningful metadata
   - Use consistent timestamp format

2. Memory Retrieval:
   - Use specific queries for better relevance
   - Limit retrieval count (k) based on context
   - Consider filtering by metadata when needed

3. Performance:
   - Clear old memories periodically
   - Monitor storage size
   - Use appropriate k values for retrieval

## Integration with Agents

The memory system integrates with AI agents through:
1. Perception storage
2. Conversation history
3. Strategic decision making
4. Behavioral pattern analysis

Example integration:

```python
class Agent:
    def __init__(self, name: str):
        self.memory = ChromaMemoryStore(f"agent_{name}")
        
    def perceive(self, game_state: str):
        self.memory.add_memory(
            text=game_state,
            metadata={
                "type": "perception",
                "timestamp": time.time()
            }
        )
        
    def make_decision(self, current_state: str):
        relevant_history = self.memory.get_relevant_memories(
            query=current_state,
            k=5
        )
        # Use relevant_history to inform decision
```

## Future Improvements

Planned enhancements:
- Support for additional vector stores
- Memory summarization
- Automatic memory pruning
- Enhanced metadata filtering
- Memory importance weighting
