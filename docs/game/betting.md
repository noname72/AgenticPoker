# Betting Module Documentation

## Overview
The betting module handles all betting-related operations in the poker game, including managing betting rounds, collecting forced bets (blinds and antes), and handling all-in situations with side pots.

## Core Functions

### handle_betting_round(game: Game) -> bool
Main entry point for managing a complete betting round.

#### Parameters:
- `game` (Game): Game instance containing all game state and player information

#### Returns:
- `bool`: Whether the game should continue (True if multiple players remain)

#### Example:
```python
# Run a betting round and check if game should continue
should_continue = handle_betting_round(game)
if not should_continue:
    # Handle end of hand
```

### betting_round(game: Game) -> None
Manages a complete round of betting among active players.

#### Parameters:
- `game` (Game): Game instance containing table, pot manager, and round state

#### Example:
```python
# Process a complete betting round
betting_round(game)

# Bets are automatically moved to pot after round completes
```

### collect_blinds_and_antes(game, dealer_index, small_blind, big_blind, ante) -> int
Collects mandatory bets (blinds and antes) at the start of each hand.

#### Parameters:
- `game` (Game): Game instance for updating game state
- `dealer_index` (int): Position of the dealer button
- `small_blind` (int): Amount of the small blind
- `big_blind` (int): Amount of the big blind
- `ante` (int): Amount of the ante (0 if no ante)

#### Returns:
- `int`: Total amount collected from blinds and antes

#### Example:
```python
collected = collect_blinds_and_antes(
    game=game,
    dealer_index=0,
    small_blind=50,
    big_blind=100,
    ante=10
)
```

## Internal Functions

### _process_betting_cycle(game: Game) -> None
Processes a single cycle of betting for all active players.

#### Key Features:
- Handles player actions in clockwise order
- Manages all-in situations
- Updates table state based on actions
- Logs betting actions and game state

#### Betting Process:
1. Gets next player to act
2. Handles all-in situations
3. Gets player's action decision
4. Executes the action
5. Updates table state
6. Checks if round is complete

## Betting Rules

### All-in Handling
- Players can bet their entire stack
- Side pots are created when players go all-in
- Players must call the full amount of an all-in bet if they have chips

### Betting Limits
- Minimum bet equals the big blind
- Maximum raise is controlled by game config:
  - max_raise_multiplier: Maximum raise as multiplier of current bet
  - max_raises_per_round: Maximum number of raises per betting round

### Betting Order
1. Small blind acts first pre-flop
2. Big blind acts last pre-flop
3. First active player after dealer acts in subsequent rounds

## Logging

The module uses BettingLogger for comprehensive action tracking:

### Key Logging Points:
- Player turns and actions
- Blind and ante collection
- All-in situations
- Betting round completion
- Error conditions

### Example Log Output:
```
[Betting] Alice's turn (Hand: A♠ K♠ Q♠ J♠ T♠, Chips: $1000)
[Betting] Current bet: $100, Pot: $150
[Betting] Active players: Alice, Bob, Charlie
[Betting] Alice raises to $200
```

## Error Handling

The module implements robust error checking:
- Validates player existence
- Ensures positive pot amounts
- Handles insufficient chips
- Manages invalid actions
- Recovers from all-in situations

## Best Practices

1. **State Management**
   - Always use game.table for player management
   - Update pot through game.pot methods
   - Track betting state in game.table

2. **Action Processing**
   - Validate actions before execution
   - Handle all-in cases explicitly
   - Update table state after each action

3. **Error Recovery**
   - Provide safe fallback actions
   - Maintain pot integrity
   - Log all error conditions

4. **Performance**
   - Minimize state updates
   - Use efficient player iteration
   - Optimize pot calculations 