# LLM Poker Agent Documentation

## Overview
The LLM (Language Learning Model) Agent is an AI poker player that uses natural language processing to make strategic decisions, interpret opponent behavior, and communicate during gameplay. It combines poker domain knowledge with configurable personality traits, cognitive mechanisms, and a persistent memory system.

## Key Updates

### Memory System Optimization
The agent now uses a more focused memory retrieval approach:

```python
def decide_action(self, game_state: str, opponent_message: Optional[str] = None) -> str:
    """Uses strategy-aware prompting with limited memory context."""
    # Get only recent relevant memories
    relevant_memories = self.memory_store.get_relevant_memories(
        query=game_state,
        k=2  # Reduced from 3 to avoid over-weighting past events
    )
    
    # Format memories for context
    memory_context = ""
    if relevant_memories:
        memory_context = "\nRecent relevant experiences:\n" + "\n".join(
            [f"- {mem['text']}" for mem in relevant_memories]
        )

    # Combine current state with memory context
    prompt = self._get_decision_prompt(game_state + memory_context)
    # ... rest of decision making process
```

### Resource Management
The agent now implements proper resource cleanup through context management:

```python
# Method 1: Explicit cleanup
agent = LLMAgent(name="Bot1")
try:
    # Use agent...
finally:
    agent.close()

# Method 2: Context manager (preferred)
with LLMAgent(name="Bot2") as agent:
    # Use agent...
    # Cleanup happens automatically
```

### Session-Specific Memory
Memory collections are now session-specific:

```python
# Initialize memory store with session-specific collection name
collection_name = f"agent_{name.lower().replace(' ', '_')}_{session_id}_memory"
self.memory_store = ChromaMemoryStore(collection_name)
```

### Best Practices Updates

1. **Memory Management**
   - Use session-specific collections
   - Limit memory retrieval to k=2 for decision making
   - Implement proper cleanup through context managers
   - Clear perception and conversation histories explicitly

2. **Resource Handling**
   - Use context managers for automatic cleanup
   - Implement explicit close() method for manual cleanup
   - Handle cleanup during interpreter shutdown
   - Clear in-memory data structures properly

3. **Error Handling**
   - Suppress errors during interpreter shutdown
   - Log warnings for non-critical cleanup issues
   - Implement retry mechanism for LLM queries
   - Provide fallback behaviors for failures
