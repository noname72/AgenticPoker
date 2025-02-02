# AI Poker Agent Documentation

The **AI Poker Agent** is an advanced AI player designed to simulate human-like decision-making, interpret opponent behavior, and communicate effectively during 5-card draw poker gameplay. Powered by natural language processing (NLP), the agent combines poker domain expertise with configurable personality traits, cognitive mechanisms, and a persistent memory system for enhanced gameplay. 

The system's design emphasizes adaptability, efficiency, and intuitive resource management, making it ideal for a variety of poker scenarios.

---

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

### Decision Making System
```python
def decide_action(self, game: "Game") -> ActionDecision:
    """Determine the next poker action based on the current game state."""
    # Get hand evaluation before making decision
    hand_eval: HandEvaluation = self.hand.evaluate() if self.hand else None

    # Plan strategy if strategy planner is enabled
    if self.use_planning:
        self.strategy_planner.plan_strategy(self, game, hand_eval)

    decided_action = self._decide_action(game, hand_eval)

    return decided_action
```

### Resource Management
The agent implements proper resource cleanup through context management:

```python
# Method 1: Explicit cleanup
agent = Agent(name="Bot1")
try:
    # Use the agent for gameplay...
finally:
    agent.close()

# Method 2: Context manager (preferred)
with Agent(name="Bot2") as agent:
    # Use agent...
    # Cleanup happens automatically
```

### Configuration Options
```python
Agent(
    name: str,
    chips: int = 1000,
    strategy_style: str = "Aggressive Bluffer",
    use_reasoning: bool = True,
    use_reflection: bool = True,
    use_planning: bool = True,
    use_opponent_modeling: bool = True,
    use_reward_learning: bool = False,
    learning_rate: float = 0.1,
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
    """Analyzes opponent patterns and playing style.
    
    Analyzes opponent patterns considering:
    - Action frequencies
    - Betting patterns
    - Position-based tendencies
    - Bluffing frequency
    - Response to aggression
    """
    stats = self.opponent_stats[opponent_name]
    
    # Calculate key metrics
    total_actions = sum(stats["actions"].values())
    aggression_frequency = (stats["actions"]["raise"] / total_actions) if total_actions > 0 else 0
    fold_to_raise_ratio = (stats["fold_to_raise_count"] / stats["raise_faced_count"]) if stats["raise_faced_count"] > 0 else 0
    bluff_success_rate = (stats["bluff_successes"] / stats["bluff_attempts"]) if stats["bluff_attempts"] > 0 else 0
    
    # Returns detailed analysis including:
    # - Primary patterns
    # - Threat level assessment
    # - Playing style classification
    # - Exploitable weaknesses
    # - Notable strengths
    # - Recommended strategic adjustments
```

### Message Generation
```python
def get_message(self, game) -> str:
    """Generate strategic table talk based on game state and style.
    
    Considers:
    - Communication style (Intimidating/Analytical/Friendly)
    - Current emotional state
    - Game state context
    - Recent table history
    
    Returns a contextually appropriate message that aligns with the agent's
    personality and strategic goals.
    """
```

### Strategy Updates
```python
def update_strategy(self, game_outcome: Dict[str, Any]) -> None:
    """Update agent's strategy based on game outcomes and performance.
    
    Analyzes:
    - Game results
    - Current strategy effectiveness
    - Recent performance history
    - Opponent adaptations
    
    Can dynamically switch between strategy styles:
    - Aggressive Bluffer
    - Calculated and Cautious
    - Chaotic and Unpredictable
    """
```

## Error Recovery

The agent implements multiple layers of error handling:

1. **Decision Making**
   - Fallback to safe actions on error
   - Retry mechanism for LLM queries
   - Validation of all decisions

2. **Memory Operations**
   - Graceful degradation on memory failures
   - Automatic cleanup of stale data
   - Recovery from connection issues

3. **Resource Management**
   - Automatic cleanup through context managers
   - Explicit cleanup methods
   - Graceful shutdown handling

## Performance Considerations

- Use appropriate memory retrieval limits
- Implement caching for frequent operations
- Clean up resources promptly
- Monitor LLM token usage
- Log performance metrics
