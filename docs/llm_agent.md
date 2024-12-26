# LLM Poker Agent Documentation

## Overview
The LLM (Language Learning Model) Agent is an AI poker player that uses natural language processing to make strategic decisions, interpret opponent behavior, and communicate during gameplay. It combines poker domain knowledge with configurable personality traits, cognitive mechanisms, and a persistent memory system.

## Core Features

### Strategic Decision Making
- Chain-of-thought reasoning for decisions
- Adaptive strategy planning
- Opponent modeling and analysis
- Reward-based learning system

### Memory Systems
- Short-term memory for recent events
- Long-term memory using ChromaDB
- Session-specific memory collections
- Efficient memory retrieval for decisions

### Communication
- Strategic message generation
- Opponent message interpretation
- Configurable communication styles
- Emotional state tracking

## Implementation Details

### Memory System
```python
def decide_action(self, game_state: str, opponent_message: Optional[str] = None) -> str:
    """Uses strategy-aware prompting with memory context."""
    try:
        # Use strategy planner if enabled
        if self.use_planning:
            plan = self.strategy_planner.plan_strategy(game_state, self.chips)
            action = self.strategy_planner.execute_action(game_state)
            return action

        # Fallback to memory-based decision making
        relevant_memories = self.memory_store.get_relevant_memories(
            query=game_state,
            k=2,
        )
        
        memory_context = ""
        if relevant_memories:
            memory_context = "\nRecent relevant experiences:\n" + "\n".join(
                [f"- {mem['text']}" for mem in relevant_memories]
            )

        prompt = self._get_decision_prompt(game_state + memory_context)
        response = self._query_llm(prompt)
        action = self._normalize_action(response.split("DECISION:")[1].strip())
        return action

    except Exception as e:
        self.logger.error(f"Decision error: {str(e)}")
        return "call"  # Safe fallback
```

### Resource Management
The agent implements proper resource cleanup through context management:

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

### Configuration Options
```python
LLMAgent(
    name: str,
    chips: int = 1000,
    strategy_style: str = "Aggressive Bluffer",
    use_reasoning: bool = True,
    use_reflection: bool = True,
    use_planning: bool = True,
    use_opponent_modeling: bool = True,
    use_reward_learning: bool = False,
    learning_rate: float = 0.1,
    config: Optional[Dict] = None,
    session_id: Optional[str] = None,
    communication_style: str = "Analytical"
)
```

## Best Practices

### Memory Management
- Use session-specific collections for isolation
- Implement proper cleanup through context managers
- Clear perception and conversation histories explicitly
- Use focused memory retrieval with appropriate limits

### Resource Handling
- Prefer context managers for automatic cleanup
- Implement explicit close() method for manual cleanup
- Handle cleanup during interpreter shutdown gracefully
- Clear in-memory data structures properly

### Error Handling
- Implement retry mechanism for LLM queries
- Provide safe fallback behaviors
- Log warnings for non-critical issues
- Suppress errors during interpreter shutdown

### Strategy Planning
- Enable strategic planning for better decision making
- Use reward-based learning when appropriate
- Implement opponent modeling for adaptive play
- Configure personality traits to match desired play style

## Advanced Features

### Opponent Modeling
```python
def analyze_opponent(self, opponent_name: str, game_state: str) -> Dict[str, Any]:
    """Analyzes opponent patterns and playing style."""
    # Tracks:
    # - Action frequencies
    # - Betting patterns
    # - Position-based tendencies
    # - Bluffing frequency
    # - Response to aggression
```

### Reward Learning
```python
def update_from_reward(self, reward: int, game_state: Dict[str, Any]) -> None:
    """Updates strategy based on rewards using temporal difference learning."""
    # Features:
    # - Records action-reward pairs
    # - Updates action values
    # - Adjusts personality traits
    # - Adapts strategy based on outcomes
```

### Strategic Communication
```python
def get_message(self, game_state: str) -> str:
    """Generates strategic table talk based on game state and style."""
    # Considers:
    # - Communication style
    # - Emotional state
    # - Strategic intent
    # - Recent game history
```
