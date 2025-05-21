# Game Module Documentation

## Overview
The Game module is the core controller for poker games, supporting both **5-Card Draw (Limit)** and **No-Limit Texas Hold'em**. It manages game flow, betting rounds, player interactions, and provides comprehensive state tracking, error handling, and detailed logging of game events.

## AgenticPoker Class

### Attributes

#### Game Configuration
- `config` (GameConfig): Configuration parameters for the game, including `game_type` (e.g., "FIVE_CARD_DRAW", "TEXAS_HOLDEM"), `max_players`, betting limits, and starting conditions.
- `session_id` (Optional[str]): Unique identifier for this game session
- `deck` (Deck): The deck of cards used for dealing
- `table` (Table): Manages players, their positions, and the current betting state (e.g., `min_raise_amount` for NLHE).
- `small_blind` (int): Required small blind bet amount
- `big_blind` (int): Required big blind bet amount
- `dealer_index` (int): Position of current dealer
- `round_number` (int): Current round number
- `max_rounds` (Optional[int]): Maximum rounds to play
- `ante` (int): Mandatory bet from all players
- `initial_chips` (Dict[Player, int]): Starting chips for each player this round.
- `game_type` (str): The type of poker game being played (e.g., "FIVE_CARD_DRAW", "TEXAS_HOLDEM"). Determined by `GameConfig`.
- `max_players` (int): Maximum number of players for the game. Determined by `GameConfig`.
- `community_cards` (List[Card]): List of community cards on the table (used in Texas Hold'em).

#### State Management
- `current_bet` (int): Current bet amount that players must match or raise.
- `pot` (Pot): Manages pot calculations and side pots.
- `last_raiser` (Optional[Player]): The last player who made a raise in the current betting round.
- `db_client` (DatabaseClient): Database connection for state persistence.

### Methods

#### __init__(players: List[Player], config: Optional[GameConfig] = None, **kwargs)
Initializes a new poker game with specified players and configuration. 
Can also accept individual parameters like `small_blind`, `big_blind`, `game_type`, `max_players` which will be used to create a `GameConfig` if one is not explicitly provided.

```python
# Initialize with GameConfig for Texas Hold'em
game_config_th = GameConfig(
    game_type="TEXAS_HOLDEM",
    max_players=6,
    starting_chips=2000,
    small_blind=10,
    big_blind=20
)
game_th = AgenticPoker(players_list, config=game_config_th)

# Initialize with GameConfig for 5-Card Draw
game_config_5cd = GameConfig(
    game_type="FIVE_CARD_DRAW",
    max_players=5,
    starting_chips=1000,
    small_blind=5,
    big_blind=10,
    max_raises_per_round=4 # Limit game
)
game_5cd = AgenticPoker(players_list, config=game_config_5cd)


# Or with direct parameters (defaults to FIVE_CARD_DRAW if game_type not specified)
game_direct = AgenticPoker(
    players_list,
    game_type="TEXAS_HOLDEM", # Specify game type
    max_players=9,
    small_blind=25,
    big_blind=50
)
```

#### play_game(max_rounds: Optional[int] = None) -> None
Executes the main game loop until completion. The game loop handles multiple rounds, and each round's specific flow depends on the `game_type`.

```python
game.play_game(max_rounds=100)  # Play up to 100 rounds
```

##### General Round Steps:
1. Check for player eliminations and game end conditions.
2. Start a new round:
    - Initialize round state (reset pot, player bets, etc.).
    - Deal cards to players (number of cards depends on `game_type`).
    - Collect blinds and antes.
3. Execute betting and card phases according to `game_type` (see "Game Flow by Type" below).
4. Handle Showdown: Evaluate hands (considering community cards for Texas Hold'em) and distribute pot(s).
5. Reset for the next round: Clear hands, rotate dealer.

##### Side Effects:
- Updates player chip counts.
- Tracks eliminated players.
- Logs game progress and detailed actions.
- Rotates dealer position.
- Updates game state (round number, pot, community cards, etc.).

### Game Types Supported

#### FIVE_CARD_DRAW
- **Objective**: Form the best 5-card poker hand after one draw.
- **Dealing**: Each player receives 5 private cards.
- **Betting Rounds**: Two (pre-draw and post-draw).
- **Draw Phase**: Players can exchange some or all of their cards once.
- **Betting Style**: Typically Limit poker (e.g., fixed bets, limited number of raises per round as defined in `GameConfig`).

#### TEXAS_HOLDEM
- **Objective**: Form the best 5-card poker hand using any combination of 2 private "hole" cards and 5 shared "community" cards.
- **Dealing**: Each player receives 2 private hole cards. 5 community cards are dealt in stages: Flop (3 cards), Turn (1 card), River (1 card).
- **Betting Rounds**: Four:
    1.  **Pre-flop**: After hole cards are dealt.
    2.  **Flop**: After the first 3 community cards are dealt.
    3.  **Turn**: After the 4th community card is dealt.
    4.  **River**: After the 5th (final) community card is dealt.
- **Betting Style**: No-Limit (players can bet any amount up to their full stack, with minimum bet and raise rules). `max_raise_multiplier` and `max_raises_per_round` in `GameConfig` are ignored (effectively `None`).

### Game Flow by Type

The `play_game` method internally calls different sequences of handler methods based on `self.game_type`.

#### Five Card Draw Game Flow
1.  `_handle_pre_draw_phase() -> bool`: Manages the pre-draw betting round.
2.  `_handle_draw_phase() -> bool`: Handles the card drawing phase where players exchange cards.
3.  `_handle_post_draw_phase() -> bool`: Manages the post-draw betting round.

```python
# Example internal calls for Five Card Draw
# should_continue = game._handle_pre_draw_phase()
# if should_continue: game._handle_draw_phase()
# if should_continue: should_continue = game._handle_post_draw_phase()
```

#### Texas Hold'em Game Flow
1.  `_handle_pre_flop_betting() -> bool`: Manages betting after hole cards are dealt.
2.  `_handle_flop_dealing_and_betting() -> bool`: Deals the flop (3 community cards) and manages the subsequent betting round.
3.  `_handle_turn_dealing_and_betting() -> bool`: Deals the turn (1 community card) and manages the subsequent betting round.
4.  `_handle_river_dealing_and_betting() -> bool`: Deals the river (1 community card) and manages the final betting round.


##### Common Method for Both Game Types
- `_handle_showdown() -> None`: Determines winners and distributes pots. For Texas Hold'em, this involves evaluating the best 5-card hand from each player's 2 hole cards and the 5 community cards.

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

1. Tournament mode support (e.g., increasing blinds).
2. Further poker variants (e.g., Omaha, Stud). Texas Hold'em (No-Limit) has now been added.
3. Enhanced state tracking for more complex agent strategies.
4. Performance optimizations for large-scale simulations.
5. Advanced AI features and more sophisticated opponent modeling.