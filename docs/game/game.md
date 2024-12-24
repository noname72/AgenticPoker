# Game Module Documentation

## Overview
The Game module is the core controller for the poker game, managing game flow, rounds, and player interactions. It implements a 5-card draw poker game with support for multiple players, side pots, and detailed logging.

## Classes

### AgenticPoker
Main game controller class that manages the poker game flow, including betting rounds, card drawing, and winner determination.

#### Attributes
- `deck (Deck)`: The deck of cards used for dealing
- `players (List[Player])`: List of currently active players in the game
- `pot (int)`: Total chips in the current pot
- `small_blind (int)`: Required small blind bet amount
- `big_blind (int)`: Required big blind bet amount
- `dealer_index (int)`: Position of current dealer (0-based, moves clockwise)
- `round_count (int)`: Number of completed game rounds
- `round_number (int)`: Current round number (increments at start of each round)
- `max_rounds (Optional[int])`: Maximum number of rounds to play, or None for unlimited
- `ante (int)`: Mandatory bet required from all players at start of each hand
- `session_id (Optional[str])`: Unique identifier for this game session
- `side_pots`: Optional list of dictionaries tracking side pots when players are all-in

#### Methods

##### `__init__(players, starting_chips=1000, small_blind=10, big_blind=20, max_rounds=None, ante=0, session_id=None)`
Initializes a new poker game.

**Parameters:**
- `players`: List of player names or Player objects
- `starting_chips`: Initial chip amount for each player
- `small_blind`: Small blind bet amount
- `big_blind`: Big blind bet amount
- `max_rounds`: Maximum number of rounds to play (None for unlimited)
- `ante`: Mandatory bet required from all players
- `session_id`: Unique identifier for this game session

##### `start_game()`
Executes the main game loop until a winner is determined or max rounds reached. Controls the overall flow including:
1. Pre-draw betting (including blinds/antes)
2. Draw phase
3. Post-draw betting
4. Showdown

##### `start_round()`
Initiates a new round of poker by:
- Incrementing round number
- Shuffling deck
- Dealing cards
- Setting dealer and blind positions
- Logging round information

##### `blinds_and_antes()`
Collects mandatory bets (blinds and antes) at the start of each hand.

##### `draw_phase()`
Handles the card drawing phase where players can discard and draw new cards.

##### `showdown()`
Manages the showdown phase, determines winners, and distributes pots. Handles:
- Main pot and side pot calculations
- Hand comparison
- Chip distribution
- Detailed logging of results

##### `handle_side_pots()`
Calculates and splits the pot when players are all-in with different amounts.

**Returns:**
- List of tuples, each containing:
  - `int`: The amount in this side pot
  - `List[Player]`: Players eligible to win this specific pot

**Example:**
```python
# With three players betting different amounts:
# Player A: $100 (all-in)
# Player B: $200 (all-in)
# Player C: $300
side_pots = game.handle_side_pots()
# Returns: [
#   (300, [player_a, player_b, player_c]),  # Main pot
#   (300, [player_b, player_c]),            # First side pot
#   (300, [player_c])                       # Second side pot
# ]
```

##### `_calculate_side_pots(posted_amounts)`
Helper method to calculate side pots based on posted amounts.

**Parameters:**
- `posted_amounts`: Dictionary mapping players to their bet amounts

**Returns:**
- List of dictionaries, each containing:
  - `amount`: Size of this side pot
  - `eligible_players`: List of player names eligible for this pot

##### `remove_bankrupt_players()`
Removes players with zero chips and checks if game should continue.

**Returns:**
- `bool`: True if game should continue, False if game should end

#### Example Usage
```python
# Initialize game with three players
players = ['Alice', 'Bob', 'Charlie']
game = AgenticPoker(
    players,
    starting_chips=1000,
    small_blind=10,
    big_blind=20,
    ante=5,
    max_rounds=100
)

# Start the game
game.start_game()
```

#### Implementation Details
- Manages complete game flow from start to finish
- Handles player eliminations and bankrupt players
- Supports side pots for all-in situations
- Provides detailed logging of all game actions
- Tracks game statistics and round information
- Ensures fair distribution of chips in all scenarios
- Supports both AI and human players through consistent interface 