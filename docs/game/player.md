# Player Module Documentation

## Overview
The Player module represents a poker player with comprehensive state management, betting capabilities, and action execution. It provides detailed logging and validation of all player operations.

## Player Class

### Attributes

#### Core Attributes
- `name` (str): Player's display name
- `chips` (int): Current chip count
- `bet` (int): Current bet amount in this round
- `hand` (Hand): Current hand of cards
- `position` (PlayerPosition): Current table position

#### State Flags
- `folded` (bool): Whether player has folded
- `is_all_in` (bool): Whether player is all-in
- `checked` (bool): Whether player has checked
- `called` (bool): Whether player has called
- `_logged_all_in` (bool): Internal flag for logging

### Methods

#### Initialization

##### __init__(name: str, chips: int = 1000)
Initialize a new player with name and starting chips.

```python
# Create new player
player = Player("Alice", chips=1000)

# Validation examples
try:
    player = Player("")  # Raises ValueError
    player = Player("Bob", chips=-100)  # Raises ValueError
except ValueError as e:
    print(f"Invalid player creation: {e}")
```

#### Betting Operations

##### place_bet(amount: int, game) -> int
Place a bet and handle all-in situations.

```python
# Normal bet
actual_bet = player.place_bet(100, game)

# All-in bet
remaining_chips = player.chips
all_in_amount = player.place_bet(remaining_chips, game)
```

##### execute(action_decision: ActionDecision, game)
Execute a poker action based on decision.

```python
# Execute different actions
player.execute(ActionDecision(ActionType.RAISE, raise_amount=200), game)
player.execute(ActionDecision(ActionType.CALL), game)
player.execute(ActionDecision(ActionType.CHECK), game)
player.execute(ActionDecision(ActionType.FOLD), game)
```

#### Internal Action Methods

##### _raise(amount: int, game) -> None
Handle raise action with proper all-in logic.

```python
# Internal raise handling
player._raise(200, game)  # Raises by 200
```

##### _call(amount: int, game) -> None
Handle call action.

```python
player._call(current_bet, game)
```

##### _check() -> None
Mark player as checked.

```python
player._check()
```

##### _fold() -> None
Mark player as folded.

```python
player._fold()
```

#### State Management

##### reset_bet() -> None
Reset bet amount for next betting round.

```python
player.reset_bet()  # Resets bet to 0
```

##### reset_for_new_round() -> None
Reset all player state for new round.

```python
player.reset_for_new_round()  # Resets all flags and hand
```

##### get_state() -> PlayerState
Get current player state.

```python
state = player.get_state()
print(f"Chips: {state.chips}")
print(f"Bet: {state.bet}")
print(f"Status: {'Folded' if state.folded else 'Active'}")
```

### Position Management

#### @property position() -> PlayerPosition
Get player's current table position.

```python
current_position = player.position
```

#### @position.setter
Set player's table position.

```python
player.position = PlayerPosition.DEALER
```

### String Representation

#### __str__() -> str
Get string representation of player state.

```python
print(player)  # "Alice (chips: 1000, folded: False)"
```

### Equality Operations

#### __eq__(other) -> bool
Compare players for equality (by name).

```python
player1 = Player("Alice")
player2 = Player("Alice")
print(player1 == player2)  # True
```

#### __hash__() -> int
Hash function for player objects.

```python
players = {player1, player2}  # Uses hash for set operations
```

## Error Handling

The Player class implements comprehensive validation:

```python
try:
    # Invalid bet amount
    player.place_bet(-100, game)  # Raises ValueError
    
    # Invalid action
    player.execute(invalid_action, game)  # Raises Exception
    
    # Invalid initialization
    Player("", chips=1000)  # Raises ValueError
    
except (ValueError, Exception) as e:
    print(f"Error: {e}")
```

## Logging

The module uses PlayerLogger for detailed operation tracking:

```python
# Examples of logged events
PlayerLogger.log_player_creation(name, chips)
PlayerLogger.log_bet_placement(name, amount, total_bet, remaining_chips, pot)
PlayerLogger.log_action_execution(name, action_type)
PlayerLogger.log_state_reset(name, context="new round")
```

## Best Practices

### 1. State Management
- Validate all state changes
- Track all-in status carefully
- Reset state appropriately
- Maintain position accuracy

### 2. Action Execution
- Validate actions before execution
- Handle all-in cases explicitly
- Track action flags properly
- Log all operations

### 3. Resource Management
- Track chips accurately
- Validate bet amounts
- Handle insufficient chips
- Maintain hand state

### 4. Error Handling
- Validate input parameters
- Provide clear error messages
- Log error conditions
- Maintain state consistency

## Related Components

The Player class interacts with:
- Hand: Card management
- Game: Game flow control
- PlayerState: State representation
- PlayerPosition: Position enumeration
- PlayerLogger: Operation logging

## Future Considerations

1. Enhanced player statistics
2. Strategy tracking
3. Historical performance
4. Extended state management
5. Tournament support 