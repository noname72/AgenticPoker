# Game Module Documentation

## Overview
The Game module is the core controller for 5-card draw poker, managing game flow, betting rounds, and player interactions. It provides comprehensive state tracking, error handling, and detailed logging of game events.

## AgenticPoker Class

### Attributes

#### Game Configuration
- `config` (GameConfig): Configuration parameters for the game
- `session_id` (Optional[str]): Unique identifier for this game session
- `deck` (Deck): The deck of cards used for dealing
- `table` (Table): Manages players and their positions
- `small_blind` (int): Required small blind bet amount
- `big_blind` (int): Required big blind bet amount
- `dealer_index` (int): Position of current dealer
- `round_number` (int): Current round number
- `max_rounds` (Optional[int]): Maximum rounds to play
- `ante` (int): Mandatory bet from all players
- `initial_chips` (Dict[Player, int]): Starting chips for each player

#### State Management
- `current_bet` (int): Current bet amount to match
- `pot` (Pot): Manages pot calculations and side pots
- `last_raiser` (Optional[Player]): Last player to raise
- `db_client` (DatabaseClient): Database connection for state persistence

### Methods

#### __init__(players: List[Player], config: Optional[GameConfig] = None, **kwargs)
Initializes a new poker game with specified players and configuration.

```python
# Initialize with GameConfig
game = AgenticPoker(
    players,
    config=GameConfig(
        starting_chips=1000,
        small_blind=50,
        big_blind=100,
        ante=10,
        session_id="20240101_120000",
        max_raise_multiplier=3,
        max_raises_per_round=4,
        min_bet=100
    )
)

# Or with direct parameters
game = AgenticPoker(
    players,
    small_blind=50,
    big_blind=100,
    ante=10
)
```

#### play_game(max_rounds: Optional[int] = None) -> None
Executes the main game loop until completion.

```python
game.play_game(max_rounds=100)  # Play up to 100 rounds
```

##### Game Flow:
1. Check for eliminations and game end conditions
2. Start new round (deal cards, collect blinds/antes)
3. Execute betting/drawing phases
4. Distribute pot to winner(s)
5. Reset for next round

##### Side Effects:
- Updates player chip counts
- Tracks eliminated players
- Logs game progress
- Rotates dealer position
- Updates game state

#### Internal Round Methods

##### _handle_pre_draw_phase() -> bool
Manages the pre-draw betting round.

```python
should_continue = game._handle_pre_draw_phase()
if not should_continue:
    # Handle early round end
```

##### _handle_draw_phase() -> bool
Handles the card drawing phase.

```python
game._handle_draw_phase()  # Players exchange cards
```

##### _handle_post_draw_phase() -> bool
Manages the post-draw betting round.

```python
should_continue = game._handle_post_draw_phase()
```

##### _handle_showdown() -> None
Determines winners and distributes pots.

```python
game._handle_showdown()  # Evaluate hands and award pots
```

### State Management

#### Game State
```python
game_state = game.get_state()
# Contains:
# - Round information
# - Player states
# - Betting information
# - Pot status
```

#### Database Integration
```python
# Save game snapshot
game.db_client.save_game_snapshot(
    session_id,
    round_number,
    game_state
)

# Save round snapshot
game.db_client.save_round_snapshot(
    session_id,
    round_number,
    round_state
)
```

### Error Handling

The game implements robust error checking:
- Validates player existence and chip counts
- Ensures positive pot amounts
- Handles insufficient chips
- Manages invalid actions
- Recovers from all-in situations

```python
try:
    game.play_game()
except ValueError as e:
    # Handle validation errors
    print(f"Game error: {e}")
finally:
    game.db_client.close()
```

### Logging

The game uses multiple loggers for comprehensive tracking:
- GameLogger: Overall game events
- BettingLogger: Betting actions
- TableLogger: Table state changes

```python
GameLogger.log_game_config(
    players=[p.name for p in table],
    starting_chips=config.starting_chips,
    small_blind=config.small_blind,
    big_blind=config.big_blind,
    ante=config.ante,
    max_rounds=config.max_rounds,
    session_id=config.session_id
)
```

## Best Practices

### 1. State Management
- Use GameConfig for configuration
- Track all state changes
- Maintain database snapshots
- Handle cleanup properly

### 2. Error Handling
- Validate all inputs
- Provide clear error messages
- Implement recovery mechanisms
- Log all errors

### 3. Resource Management
- Close database connections
- Clean up memory
- Handle session cleanup
- Manage logging resources

### 4. Game Flow
- Check state before actions
- Validate betting rounds
- Track player eliminations
- Maintain pot integrity

## Related Components

The Game class interacts with:
- Player: Player management
- Table: Position tracking
- Pot: Pot calculations
- Deck: Card management
- Hand: Card combinations
- GameConfig: Configuration
- DatabaseClient: State persistence

## Future Considerations

1. Tournament mode support
2. Additional poker variants
3. Enhanced state tracking
4. Performance optimizations
5. Advanced AI features 