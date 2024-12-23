# Game Module Documentation

## Overview
The Game module is the core controller for the poker game, managing game flow, rounds, and player interactions.

## Classes

### AgenticPoker
Main game controller class that manages the poker game flow.

#### Attributes
- `deck`: Current deck of cards
- `players`: List of active players
- `pot`: Current pot amount
- `small_blind`: Small blind amount
- `big_blind`: Big blind amount
- `dealer_index`: Current dealer position
- `round_count`: Number of completed rounds
- `ante`: Mandatory ante amount

#### Methods

##### `__init__(players, starting_chips=1000, small_blind=10, big_blind=20, max_rounds=None, ante=0, session_id=None)`
Initializes a new poker game.

##### `start_game()`
Begins the main game loop until a winner is determined.

##### `start_round()`
Initiates a new round of poker.

##### `draw_phase()`
Handles the card drawing phase.

##### `showdown()`
Manages the showdown phase and determines winners.

#### Example
```python
game = AgenticPoker(players, starting_chips=1000, small_blind=10, big_blind=20)
game.start_game()
```

#### Implementation Details
- Manages complete game flow
- Handles player eliminations
- Tracks game statistics
- Provides detailed logging 