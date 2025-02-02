# Strategy Planner Documentation

## Overview
The StrategyPlanner class manages strategic decision-making for poker agents, handling plan generation, validation, execution, and automatic renewal based on game conditions. It uses LLM-based decision making for both strategy planning and action execution.

## StrategyPlanner Class

### Attributes

#### Configuration
- `strategy_style` (str): Playing style used for planning (e.g., 'aggressive', 'conservative')
- `plan_duration` (float): Duration in seconds for which a plan remains valid
- `REPLAN_STACK_THRESHOLD` (int): Stack size change that triggers a replan

#### State
- `current_plan` (Optional[Plan]): Currently active strategic plan
- `last_metrics` (Optional[dict]): Last recorded game metrics used for planning

### Methods

#### Initialization

##### __init__(strategy_style: str, plan_duration: float = DEFAULT_PLAN_DURATION, replan_threshold: int = REPLAN_STACK_THRESHOLD)
Initialize the strategy planner with configuration parameters.

```python
planner = StrategyPlanner(
    strategy_style="Aggressive Bluffer",
    plan_duration=30.0,  # seconds
    replan_threshold=100  # chips
)
```

#### Strategy Management

##### plan_strategy(player: Player, game: Game, hand_eval: Optional[HandEvaluation] = None) -> None
Generate or update the agent's strategic plan based on current game state.

```python
# Generate new plan
planner.plan_strategy(
    player=current_player,
    game=game_instance,
    hand_eval=hand_evaluation
)
```

##### requires_replanning(game: Game, player: Player) -> bool
Determine if current game state requires a new strategic plan.

```python
if planner.requires_replanning(game, player):
    planner.plan_strategy(player, game)
```

#### Plan Creation

##### _create_default_plan() -> Plan
Create a default Plan object when errors occur or no plan is available.

```python
# Default plan structure
default_plan = planner._create_default_plan()
# Returns:
# Plan(
#     approach=Approach.BALANCED,
#     reasoning="Default fallback plan due to error",
#     bet_sizing=BetSizing.MEDIUM,
#     bluff_threshold=0.5,
#     fold_threshold=0.3,
#     expiry=time.time() + DEFAULT_PLAN_DURATION,
#     adjustments=[],
#     target_opponent=None
# )
```

##### _create_plan_from_response(plan_data: dict) -> Plan
Create a Plan object from LLM response data with validation.

```python
plan_data = {
    "approach": "aggressive",
    "reasoning": "Strong hand in late position",
    "bet_sizing": "large",
    "bluff_threshold": 0.7,
    "fold_threshold": 0.2
}
plan = planner._create_plan_from_response(plan_data)
```

## Plan Structure

### Plan Class
```python
class Plan:
    approach: Approach        # Strategy approach (AGGRESSIVE/BALANCED/DEFENSIVE)
    reasoning: str           # Explanation of strategic choices
    bet_sizing: BetSizing    # Betting size preference
    bluff_threshold: float   # Threshold for bluffing decisions (0.0-1.0)
    fold_threshold: float    # Threshold for folding decisions (0.0-1.0)
    expiry: float           # Timestamp when plan expires
    adjustments: List[str]   # List of strategic adjustments
    target_opponent: Optional[str]  # Specific opponent being targeted
```

### Enums

#### Approach
```python
class Approach(Enum):
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    DEFENSIVE = "defensive"
```

#### BetSizing
```python
class BetSizing(Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
```

## Error Handling

The planner implements comprehensive error handling:

```python
try:
    planner.plan_strategy(player, game)
except Exception as e:
    StrategyLogger.log_plan_error(e)
    # Falls back to default plan
```

## Logging

The module uses StrategyLogger for operation tracking:

```python
# Examples of logged events
StrategyLogger.log_new_plan(plan)
StrategyLogger.log_plan_reuse(plan)
StrategyLogger.log_plan_error(error)
StrategyLogger.log_planning_check(message)
StrategyLogger.log_replan_error(error)
```

## Best Practices

### 1. Plan Management
- Validate plan data
- Handle plan expiration
- Track plan metrics
- Log plan changes

### 2. Error Recovery
- Use default plans on failure
- Log error conditions
- Maintain strategy consistency
- Handle API failures

### 3. Performance
- Cache plan evaluations
- Minimize replanning
- Optimize metric tracking
- Handle timeouts

### 4. Strategy Execution
- Validate game state
- Check plan validity
- Track execution metrics
- Handle edge cases

## Related Components

The StrategyPlanner interacts with:
- Player: Player state and actions
- Game: Game state information
- Plan: Strategy representation
- LLMResponseGenerator: Plan generation
- StrategyLogger: Operation logging

## Future Considerations

1. **Enhanced Planning**
   - Multi-round strategy
   - Opponent modeling
   - Pattern recognition
   - Historical analysis

2. **Performance Optimization**
   - Caching mechanisms
   - Batch processing
   - Async operations
   - Resource management

3. **Advanced Features**
   - Tournament adaptation
   - Team coordination
   - Dynamic thresholds
   - Learning integration

4. **Monitoring**
   - Performance metrics
   - Strategy effectiveness
   - Error patterns
   - Resource usage
