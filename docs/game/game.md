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
- `round_starting_stacks (Dict[Player, int])`: Records chip counts at start of each round

#### Methods

##### `__init__(players, starting_chips=1000, small_blind=10, big_blind=20, max_rounds=None, ante=0, session_id=None)`
Initializes a new poker game with specified parameters.

**Parameters:**
- `players`: List of player names or Player objects
- `starting_chips`: Initial chip amount for each player
- `small_blind`: Small blind bet amount
- `big_blind`: Big blind bet amount
- `max_rounds`: Maximum number of rounds to play (None for unlimited)
- `ante`: Mandatory bet required from all players
- `session_id`: Unique identifier for this game session

**Side Effects:**
- Creates Player objects if names provided
- Initializes game state attributes
- Sets up logging with session context
- Logs initial game configuration

**Example:**
```python
game = AgenticPoker(['Alice', 'Bob'], starting_chips=500)
game = AgenticPoker(player_list, small_blind=5, big_blind=10, ante=1)

Game Configuration
=================================================
Players: Alice, Bob
Starting chips: $500
Blinds: $5/$10
Ante: $1
=================================================
```

##### `start_round()`
Initializes a new round of poker by setting up game state and dealing cards.

**Steps:**
1. Increments round number
2. Resets pot to zero
3. Rotates dealer position
4. Records starting chip counts
5. Shuffles deck and deals hands
6. Resets player states (bets, folded status)
7. Logs round information

**Side Effects:**
- Updates game state (round_number, pot, dealer_index, round_starting_stacks)
- Modifies player state (hand, bet, folded status)
- Creates new shuffled deck
- Logs round setup information

**Example:**
```python
game.start_round()
=================================================
Round 42
=================================================

Starting stacks (before antes/blinds):
  Alice: $1200
  Bob: $800
  Charlie: $15 (short stack)

Dealer: Alice
Small Blind: Bob
Big Blind: Charlie
```

##### `blinds_and_antes()`
Collects mandatory bets at the start of each hand.

**Process:**
1. Collects antes from all players (if any)
2. Collects small blind from player left of dealer
3. Collects big blind from player left of small blind

**Features:**
- Handles partial postings for short stacks
- Creates side pots for all-in situations
- Tracks posted amounts accurately
- Handles special cases (missing blinds, short stacks)

**Example:**
```python
game.blinds_and_antes()

Collecting antes...
Alice posts ante of $1
Bob posts ante of $1
Charlie posts ante of $1 (all in)

Bob posts small blind of $10
Charlie posts partial big blind of $5 (all in)

Starting pot: $18
  Includes $3 in antes

Side pots:
  Pot 1: $15 (Eligible: Alice, Bob)
  Pot 2: $3 (Eligible: Alice, Bob, Charlie)
```

##### `draw_phase()`
Handles the card drawing phase where players can exchange cards.

**Features:**
- Players can discard 0-5 cards and draw replacements
- Tracks discarded cards to prevent redealing
- Reshuffles discards if deck runs low
- Handles AI player decision-making
- Maintains exactly 5 cards per hand

**Example:**
```python
game.draw_phase()
--- Draw Phase ---

Alice's turn to draw
Current hand: A♠ K♠ 3♣ 4♥ 7♦
Discarding cards at positions: [2, 3, 4]
Drew 3 new cards: Q♣, J♥, 10♦
```

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