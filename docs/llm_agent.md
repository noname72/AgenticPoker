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
- Maintain session-specific long-term memory
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
   - Session-specific collections

2. **Conversation Memory**
   - Table talk
   - Opponent messages
   - Own responses
   - Communication patterns
   - Limited to recent context

3. **Strategic Memory**
   - Past decisions
   - Outcome analysis
   - Pattern recognition
   - Strategy adaptations
   - Weighted by recency

### Memory Integration in Decision Making
The agent now uses a more refined approach to memory integration:

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

### Configuration Updates
When creating an agent, you must now provide a session ID:

```python
agent = LLMAgent(
    "Alice",
    chips=1000,
    strategy_style="Aggressive Bluffer",
    session_id="20241223_173937",  # Required for memory persistence
)
```

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

### Reward Learning System
The agent includes an optional reward-based learning system that:

1. **Action Value Learning**
   - Maintains value estimates for each action type
   - Updates values using temporal difference learning
   - Balances exploration and exploitation
   - Adapts to successful and unsuccessful outcomes

2. **Dynamic Trait Adjustment**
   - Modifies personality traits based on outcomes
   - Increases risk tolerance after successful all-ins
   - Adjusts bluff frequency based on success rate
   - Maintains trait bounds (0.0-1.0)

3. **Exploration Strategy**
   - Uses epsilon-greedy exploration (10% random actions)
   - Converts action values to probabilities using softmax
   - Maintains balance between learning and performance
   - Tracks action history for analysis

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
    use_reward_learning: bool = False,           # Enable reward-based learning
    learning_rate: float = 0.1,                  # Learning rate for rewards
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

### Reward Learning Configuration
When reward learning is enabled:
```python
agent = LLMAgent(
    "Alice",
    use_reward_learning=True,
    learning_rate=0.1  # Adjusts how quickly agent learns
)
```

The agent maintains:
```python
{
    "action_values": {
        "fold": 0.0,
        "call": 0.0,
        "raise": 0.0
    },
    "reward_weights": {
        "chip_gain": 1.0,
        "win_rate": 0.8,
        "bluff_success": 0.6,
        "position_value": 0.4
    }
}
```

## Strategy Management

### Strategy Cards System
The agent uses a flexible strategy cards system that combines:

1. **Core Strategy Personalities**
   ```python
   CORE_STRATEGIES = {
       "Aggressive Bluffer": """You are an aggressive poker player who:
       - Raises frequently to put pressure on opponents
       - Uses position and timing for maximum effect
       - Bluffs often but with strategic timing
       - Seeks to dominate the table psychologically
       - Takes calculated risks to build big pots
       - Watches for signs of weakness to exploit""",
       
       "Calculated and Cautious": """You are a mathematical poker player who:
       - Makes decisions based primarily on pot odds and equity
       - Plays a tight-aggressive style
       - Bluffs rarely and only with strong drawing hands
       - Takes detailed notes on opponent patterns
       - Preserves chips for optimal spots
       - Focuses on long-term expected value""",
       
       "Chaotic and Unpredictable": """You are an unpredictable player who:
       - Varies play style dramatically hand to hand
       - Makes unconventional plays to confuse opponents
       - Talks frequently to create table atmosphere
       - Takes unusual lines with marginal hands
       - Switches between passive and aggressive
       - Uses psychology over pure math"""
   }
   ```

2. **Situational Modifiers**
   ```python
   SITUATION_MODIFIERS = {
       "short_stack": "Adjusts for < 300 chips",
       "big_stack": "Adjusts for > 2000 chips",
       "bubble": "Adjusts for tournament bubble",
       "all_in": "Adjusts for all-in situations and side pots"
   }
   ```

3. **Cognitive Modules**
   ```python
   COGNITIVE_MODULES = {
       "reasoning": "Step-by-step decision analysis",
       "reflection": "Review and validate decisions",
       "planning": "Multi-step strategic planning"
   }
   ```

### Strategy Manager
The agent uses a StrategyManager class to:
- Combine different strategy components
- Generate complete prompts
- Handle strategy updates
- Manage cognitive modules

```python
strategy_manager = StrategyManager(
    base_strategy="Aggressive Bluffer",
)

# Enable cognitive modules
strategy_manager.active_modules.update({
    "reasoning": True,
    "reflection": True,
    "planning": True
})
```

### Dynamic Strategy Adaptation
The strategy manager:
1. Automatically detects game situations
2. Applies relevant modifiers
3. Activates appropriate cognitive modules
4. Generates comprehensive strategy prompts

Example prompt generation:
```python
prompt = strategy_manager.get_complete_prompt({
    "chips": 250,  # Triggers short stack modifier
    "is_bubble": True  # Triggers bubble play modifier
})
```

### Decision Making Process
The agent's decision-making process now includes awareness of side pots:

1. **Game State Analysis**
   - Evaluates current pot and any side pots
   - Considers eligibility for different pots
   - Adjusts strategy based on all-in situations

2. **Side Pot Considerations**
   ```python
   def _analyze_side_pots(self, game_state: str) -> Dict[str, Any]:
       """Analyzes side pot situation for strategic decision making."""
       return {
           "is_all_in": self.chips == 0,
           "eligible_pots": self._get_eligible_pots(game_state),
           "total_equity": self._calculate_pot_equity(game_state)
       }
   ```

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

### Reward Learning Usage
```python
# Create agent with reward learning
learning_agent = LLMAgent(
    "Alice",
    strategy_style="Aggressive Bluffer",
    use_reward_learning=True,
    learning_rate=0.1
)

# Update agent based on game outcome
learning_agent.update_from_reward(
    reward=100,  # Positive reward for winning
    game_state={
        "all_in": True,
        "bluff_successful": True,
        "position": "dealer"
    }
)
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

### Reward Learning Impact
- Memory Usage: ~1KB per 100 actions stored
- Update Time: <5ms per reward update
- Learning Convergence: ~100 hands for stable values
- Exploration Overhead: 10% random actions

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

### Reward Learning Limitations
1. **Cold Start**
   - Initial random exploration phase
   - Requires sufficient samples per action
   - May make suboptimal early decisions

2. **Learning Stability**
   - Sensitive to learning rate selection
   - May overfit to recent outcomes
   - Requires balance of exploration/exploitation

3. **Memory Requirements**
   - Grows with action history size
   - May need periodic pruning
   - State space complexity

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

### Reward Learning Enhancements
1. **Advanced Learning**
   - Implement prioritized experience replay
   - Add state-dependent action values
   - Introduce multi-step returns
   - Implement eligibility traces

2. **Optimization**
   - Batch updates for efficiency
   - Adaptive learning rates
   - Selective memory retention
   - Feature-based state representation

3. **Integration**
   - Combine with opponent modeling
   - Adaptive exploration rates
   - Context-aware rewards
   - Meta-learning capabilities

## Decision Making Process

The agent's decision-making process now incorporates the strategy cards system:

1. **Strategy Compilation**
   - Combines core strategy with situational modifiers
   - Activates relevant cognitive modules
   - Generates comprehensive strategy prompt

2. **Decision Generation**
   ```python
   def _get_decision_prompt(self, game_state: str) -> str:
       """Creates a decision prompt combining strategy and game state."""
       strategy_prompt = self.strategy_manager.get_complete_prompt({
           "chips": self.chips,
           "is_bubble": self._is_bubble_situation(game_state),
       })
       
       return f"""
       {strategy_prompt}
       
       Current situation:
       {game_state}
       
       Based on your strategy and the current situation, what action will you take?
       Respond with DECISION: <fold/call/raise> and brief reasoning
       """
   ```

3. **Action Execution**
   - Parses LLM response for DECISION directive
   - Normalizes action to valid poker move
   - Provides fallback to 'call' if needed

When creating an agent, you can now specify which cognitive modules to enable:

```python
agent = LLMAgent(
    "Alice",
    strategy_style="Aggressive Bluffer",
    use_reasoning=True,    # Enables reasoning module
    use_reflection=True,   # Enables reflection module
    use_planning=True,     # Enables planning module
)
```

The strategy manager will automatically:
- Load the appropriate core strategy
- Enable specified cognitive modules
- Handle situational adaptations