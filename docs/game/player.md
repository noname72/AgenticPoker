# Player Module Documentation

## Overview
The Player module represents a poker player, managing their chips, bets, and game state.

## Classes

### Player
Represents a poker player with chips and betting capability.

#### Attributes:
- `name`: Player's display name
- `chips`: Current chip count
- `bet`: Current bet amount
- `folded`: Fold status
- `hand`: Current Hand object

#### Methods:

##### __init__(name, chips=1000)
Initialize a new player.

##### place_bet(amount)
Place a bet and return actual amount bet.

##### fold()
Mark player as folded.

##### reset_bet()
Reset current bet to zero.

##### reset_for_new_round()
Reset player state for new round.

#### Example:
```python
player = Player("Alice", chips=1000)
actual_bet = player.place_bet(100)
```

#### Implementation Details:
- Manages player resources
- Tracks betting history
- Handles all-in situations
- Provides state management 