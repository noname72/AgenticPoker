# LLM Poker Agent Documentation

## Overview
The LLM (Language Learning Model) Agent is an AI poker player that uses natural language processing to make strategic decisions, interpret opponent behavior, and communicate during gameplay. It combines poker domain knowledge with configurable personality traits, cognitive mechanisms, and a persistent memory system.

## Features

### Core Capabilities
- Strategic decision making (fold/call/raise)
- Opponent message interpretation
- Natural language communication
- Adaptive strategy updates
- Hand evaluation and drawing decisions
- Historical perception tracking
- Persistent memory with vector storage
- Opponent modeling and analysis
- Statistical tracking of player behavior
- Adaptive response to opponent patterns

### Memory System
The agent uses a vector-based memory store to:
- Maintain long-term memory across games
- Store and retrieve relevant experiences
- Track conversation history
- Analyze opponent patterns
- Support strategic decision-making

Memory types include:
1. **Perception Memory**
   - Game states
   - Opponent actions
   - Hand histories
   - Timestamps and metadata

2. **Conversation Memory**
   - Table talk
   - Opponent messages
   - Own responses
   - Communication patterns

3. **Strategic Memory**
   - Past decisions
   - Outcome analysis
   - Pattern recognition
   - Strategy adaptations

### Opponent Modeling System
The agent includes an optional opponent modeling system that:

1. **Statistical Tracking**
   - Action frequencies
   - Betting patterns
   - Position-based tendencies
   - Bluffing frequency and success rates
   - Historical hand information

2. **Real-time Analysis**
   - Threat level assessment
   - Playing style classification
   - Pattern identification
   - Weakness/strength analysis
   - Strategic adjustment recommendations

3. **Adaptive Response**
   - Adjusts bluffing threshold based on opponent type
   - Modifies fold threshold based on aggression levels
   - Updates strategy based on observed patterns
   - Maintains confidence levels in analysis

### Cognitive Mechanisms
The agent has three optional cognitive mechanisms that can be enabled/disabled:

1. **Chain-of-Thought Reasoning** (`use_reasoning`)
   - Systematic step-by-step analysis of the situation
   - Considers hand strength, strategy, opponent behavior, pot odds, and personality alignment
   - Incorporates relevant historical memories
   - More thorough but computationally intensive

2. **Self-Reflection** (`use_reflection`)
   - Reviews initial decisions for consistency
   - Can revise actions that don't align with strategy/personality
   - Uses memory to validate decisions against past experiences
   - Adds an extra layer of strategic coherence

3. **Strategic Planning** (`use_planning`)
   - Develops high-level strategic plans for gameplay
   - Plans persist for configurable duration (default 30s)
   - Considers chip stack, position, and opponent patterns
   - Uses memory to inform planning decisions
   - Separates strategic planning from tactical execution

## Configuration

### Initialization Parameters
```python
LLMAgent(
    name: str,                                    # Agent's name
    chips: int = 1000,                           # Starting chips
    strategy_style: Optional[str] = None,         # Playing style
    personality_traits: Optional[Dict] = None,    # Behavioral traits
    max_retries: int = 3,                        # LLM query retries
    retry_delay: float = 1.0,                    # Retry wait time
    use_reasoning: bool = True,                  # Enable reasoning
    use_reflection: bool = True,                 # Enable reflection
    use_planning: bool = True,                   # Enable planning
    use_opponent_modeling: bool = False,         # Enable opponent modeling
    config: Optional[Dict] = None,               # Configuration dictionary
)
```

### Strategy Styles
Available poker playing styles:
- `"Aggressive Bluffer"`
- `"Calculated and Cautious"`
- `"Chaotic and Unpredictable"`

### Personality Traits
Configurable traits (0.0 to 1.0):
- `aggression`: Tendency to bet and raise
- `bluff_frequency`: Frequency of bluffing
- `risk_tolerance`: Willingness to take risks

### Planning Parameters
When planning is enabled:
- `plan_duration`: How long plans remain valid (default 30s)
- `approach`: aggressive/defensive/deceptive/balanced
- `bet_sizing`: small/medium/large
- `bluff_threshold`: When to consider bluffing (0.0-1.0)
- `fold_threshold`: When to consider folding (0.0-1.0)

## Usage Examples

### Basic Agent Creation with Memory
```python
agent = LLMAgent(
    "Alice",
    chips=1000,
    strategy_style="Aggressive Bluffer"
)
# Memory is automatically initialized and persisted
```

### Accessing Agent Memory
```python
# Get relevant memories for current situation
memories = agent.memory_store.get_relevant_memories(
    query="opponent bluffing patterns",
    k=3
)

# Add a new observation to memory
agent.memory_store.add_memory(
    text="Opponent shows aggressive betting on weak hands",
    metadata={
        "type": "observation",
        "timestamp": time.time(),
        "strategy_style": agent.strategy_style
    }
)
```

### Customized Agent with Specific Traits
```python
agent = LLMAgent(
    "Bob",
    chips=1000,
    strategy_style="Calculated and Cautious",
    personality_traits={
        "aggression": 0.3,
        "bluff_frequency": 0.2,
        "risk_tolerance": 0.4
    },
    use_reasoning=True,
    use_reflection=False,
    use_planning=True
)
```

### Different Cognitive Configurations
```python
# Full cognitive capabilities
strategic_agent = LLMAgent(
    "Alice",
    strategy_style="Calculated and Cautious",
    use_reasoning=True,
    use_reflection=True,
    use_planning=True
)

# Basic agent without advanced cognition
simple_agent = LLMAgent(
    "Bob",
    strategy_style="Aggressive Bluffer",
    use_reasoning=False,
    use_reflection=False,
    use_planning=False
)
```

### Agent with Opponent Modeling
```python
# Create agent with opponent modeling enabled
strategic_agent = LLMAgent(
    "Alice",
    strategy_style="Calculated and Cautious",
    use_opponent_modeling=True,
    personality_traits={
        "aggression": 0.6,
        "bluff_frequency": 0.4,
        "risk_tolerance": 0.5
    }
)

# Access opponent analysis
opponent_analysis = strategic_agent.analyze_opponent(
    opponent_name="Bob",
    game_state="Current game situation..."
)

# Update opponent statistics
strategic_agent.update_opponent_stats(
    opponent_name="Bob",
    action="raise",
    amount=100,
    position="dealer",
    was_bluff=False
)
```

### Opponent Analysis Structure
```python
{
    "patterns": "aggressive raising from position",
    "threat_level": "high",
    "style": "tight-aggressive",
    "weaknesses": ["folds too often to re-raises"],
    "strengths": ["strong position play"],
    "recommended_adjustments": ["increase re-raising frequency"]
}
```

## Key Methods

### Decision Making
- `get_action(game_state: str, opponent_message: Optional[str]) -> str`
  - Determines next poker action (fold/call/raise)
  - Uses reasoning, reflection, and planning if enabled

### Message Handling
- `interpret_message(opponent_message: str) -> str`
  - Analyzes opponent messages
  - Returns interpretation (trust/ignore/counter-bluff)

### Strategy Management
- `update_strategy(game_outcome: Dict[str, Any]) -> None`
  - Adapts strategy based on game results
  - Can switch between different playing styles

### State Management
- `reset_state() -> None`
  - Clears perception and conversation history
  - Maintains strategy and personality

### Strategic Planning
- `plan_strategy(game_state: str) -> Dict[str, Any]`
  - Develops high-level strategic plan
  - Plans include approach, bet sizing, and thresholds
- `execute_action(plan: Dict[str, Any], game_state: str) -> str`
  - Executes tactical decisions based on current plan

### Memory Management
- `perceive(game_state: str, opponent_message: str) -> Dict[str, Any]`
  - Processes and stores new game state information
  - Updates both short-term and long-term memory
  - Returns the processed perception data

- `_get_strategic_message(game_state: str) -> str`
  - Generates messages using memory context
  - Considers conversation history
  - Retrieves relevant past interactions

### Opponent Modeling
- `analyze_opponent(opponent_name: str, game_state: str) -> Dict[str, Any]`
  - Analyzes opponent's playing patterns and style
  - Returns detailed analysis with threat assessment
  - Includes strategic recommendations

- `update_opponent_stats(opponent_name: str, **kwargs) -> None`
  - Updates statistical tracking for opponent
  - Tracks actions, positions, and outcomes
  - Maintains running statistics

## Performance Considerations

### Computational Impact
- Reasoning mechanism: ~2x base computation time
- Reflection mechanism: ~1.5x base computation time
- Planning mechanism: ~1.8x base computation time
- All enabled: ~4x base computation time

### Token Usage
- Basic prompt: ~50 tokens
- With reasoning: ~150 tokens
- With reflection: Additional ~100 tokens
- With planning: Additional ~200 tokens

### Response Times
- Basic decision: ~1-2 seconds
- With reasoning: ~2-3 seconds
- With reflection: ~3-4 seconds
- With planning: ~3-5 seconds

### Memory Impact
- Disk Usage: ~100MB per 1000 memories
- Retrieval Time: ~50ms per query
- Storage Time: ~30ms per memory
- Vector Embedding: ~100ms per text

### Opponent Modeling Impact
- Memory Usage: ~50KB per opponent
- Analysis Time: ~200ms per opponent
- Storage Overhead: Minimal (uses defaultdict)
- Update Time: <10ms per action

## Best Practices

1. **Configuration Selection**
   - Use full cognitive capabilities for strategic depth
   - Disable for faster gameplay or testing
   - Mix configurations to study impact

2. **Strategy Style Selection**
   - Match strategy to personality traits
   - Consider table dynamics
   - Use for creating diverse player pools

3. **Error Handling**
   - Agent falls back to "call" on LLM errors
   - Implements retry mechanism for failed queries
   - Logs all decision-making steps

4. **Planning Usage**
   - Enable for long-term strategic play
   - Consider disabling in time-critical situations
   - Use with reasoning for best results

5. **Memory Management**
   - Regular memory clearing between games
   - Specific queries for better retrieval
   - Balanced memory retention
   - Consistent metadata structure

### Opponent Modeling Usage
1. **Enable Selectively**
   - Use for serious gameplay
   - Disable for casual or fast games
   - Consider memory implications

2. **Data Collection**
   - Allow sufficient actions for accurate analysis
   - Track across multiple games when possible
   - Reset statistics periodically

3. **Analysis Integration**
   - Combine with planning for best results
   - Use threat levels to adjust strategy
   - Consider confidence levels in analysis

## Limitations

1. **Response Time**
   - Multiple LLM calls can slow gameplay
   - Network latency affects performance
   - Consider timeout settings

2. **Token Usage**
   - Higher costs with cognitive mechanisms
   - Memory limitations with long histories
   - Balance detail vs. efficiency

3. **Strategy Consistency**
   - May show occasional inconsistent behavior
   - Personality drift over long sessions
   - Requires monitoring and adjustment

4. **Memory Constraints**
   - Storage space requirements
   - Retrieval latency
   - Embedding quality impact
   - Context window limits

### Opponent Modeling Limitations
1. **Cold Start**
   - Requires sufficient data for accurate analysis
   - Initial predictions may be unreliable
   - Default to conservative estimates

2. **Memory Requirements**
   - Scales with number of opponents
   - Grows with game history
   - May need periodic pruning

3. **Analysis Accuracy**
   - Dependent on data quality
   - May misclassify complex patterns
   - Requires validation over time

## Future Improvements

1. **Planned Features**
   - Improved hand reading capabilities
   - Dynamic personality adaptation
   - Multi-model support

2. **Optimization Opportunities**
   - Batch processing for decisions
   - Caching frequent patterns
   - Reduced token usage

3. **Integration Points**
   - Tournament support
   - Performance analytics
   - Strategy training

4. **Memory Enhancements**
   - Memory summarization
   - Automatic pruning
   - Importance weighting
   - Cross-game learning
   - Enhanced metadata filtering

5. **Storage Optimizations**
   - Compressed embeddings
   - Tiered storage
   - Batch operations
   - Memory indexing

### Opponent Modeling Enhancements
1. **Pattern Recognition**
   - Deep learning integration
   - Pattern sequence analysis
   - Temporal pattern detection

2. **Analysis Refinement**
   - Confidence scoring
   - Bias detection
   - Cross-validation

3. **Performance Optimization**
   - Batch analysis
   - Incremental updates
   - Compressed statistics