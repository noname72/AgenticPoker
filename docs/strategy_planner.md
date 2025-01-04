# Strategy Planner

The StrategyPlanner class handles strategic planning and execution for poker agents. It manages the creation, validation, and execution of strategic plans based on the current game state.

## Overview

The StrategyPlanner provides:
- Dynamic strategy generation based on game state
- Plan execution and action selection
- Automatic plan expiration and renewal
- Game state metric extraction and analysis
- Configurable planning thresholds

## Usage

```python
from openai import OpenAI
from agents.strategy_planner import StrategyPlanner

# Initialize planner
planner = StrategyPlanner(
    strategy_style="Aggressive Bluffer",
    client=OpenAI(),
    plan_duration=30.0  # seconds
)

# Generate a plan
game_state = "pot: $200, current_bet: $50, position: dealer..."
plan = planner.plan_strategy(game_state, chips=1000)

# Execute action based on plan
action = planner.execute_action(game_state)  # returns 'fold', 'call', or 'raise'
```

## Strategic Plans

Plans are generated through LLM queries and follow this format:
```python
{
    "approach": "aggressive/balanced/defensive",
    "reasoning": "Brief explanation of strategy",
    "bet_sizing": "small/medium/large",
    "bluff_threshold": 0.0-1.0,  # Probability threshold for bluffing
    "fold_threshold": 0.0-1.0    # Probability threshold for folding
}
```

The plan includes specific thresholds used to guide decision-making and is automatically renewed after expiration (default 30 seconds) or when significant game state changes occur.

## Replanning Triggers

The planner automatically triggers replanning when:
- Current plan expires (default 30 seconds)
- Significant bet sizes (>30% of stack)
- Low chip stack (<300)
- Position changes to late position
- Large pot relative to stack (>50%)
- All-in situations
- Tournament bubble situations

## Game State Metrics

The planner extracts and tracks key metrics:
- Current chip stack
- Current bet size
- Pot size
- Position information
- Game stage indicators

## Error Handling

The planner includes robust error handling:
- Safe fallback plans when generation fails
- Default "call" action on execution errors
- Metric extraction error recovery
- Plan validation checks

## Configuration

Key configuration options:
- `strategy_style`: Base strategy approach
- `plan_duration`: How long plans remain valid
- `client`: OpenAI client for LLM queries

## Methods

### plan_strategy(game_state: str, chips: int) -> Dict[str, Any]
Generates a new strategic plan based on current game state and chip stack.

### execute_action(game_state: str, hand_eval: Optional[Tuple[int, List[int], str]] = None) -> str
Executes the current plan to determine specific poker action. Takes into account:
- Current game state
- Hand evaluation (rank, tiebreakers, description)
- Plan thresholds and approach
- Premium hand overrides for straights or better

### _requires_replanning(game_state: str) -> bool
Internal method to check if current situation requires new plan.

### _extract_game_metrics(game_state: str) -> Dict[str, int]
Internal method to parse numerical values from game state.

## Future Improvements

1. **Enhanced Plan Generation**
   - Multi-round planning
   - Opponent-specific adaptations
   - Historical performance weighting

2. **Metric Tracking**
   - More sophisticated game state parsing
   - Pattern recognition in metrics
   - Trend analysis

3. **Plan Optimization**
   - Dynamic threshold adjustment
   - Learning from successful plans
   - Cross-game strategy adaptation

4. **Integration Points**
   - Tournament-specific planning
   - Team game coordination
   - Real-time strategy updates

## LLM Integration

The planner uses OpenAI's GPT-3.5-turbo model with:
- Temperature: 0.7 for controlled variability
- Structured prompt formats for planning and execution
- Error handling for API failures

## Strategic Overrides

The planner includes automatic overrides for premium hands:
- Prevents folding with strong hands (straight or better) unless pot odds are terrible
- Upgrades calls to raises with premium hands when using aggressive approach
- Considers pot odds when making override decisions
