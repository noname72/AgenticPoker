# Repository Module Documentation

## Overview
The Repository module provides database access patterns for the poker game, implementing the repository pattern for clean separation of data access logic.

## Classes

### BaseRepository
Base class providing common database transaction operations.

#### Methods:
- `__init__(session)`: Initialize with database session
- `commit()`: Commit current transaction
- `rollback()`: Rollback current transaction

### GameRepository
Manages game-related database operations.

#### Methods:
- `create(small_blind, big_blind, ante=0, max_players=6, game_type="5-card-draw")`: Create new game
- `get_by_id(game_id)`: Retrieve game by ID
- `get_active_games()`: Get all active games
- `update(game_id, **kwargs)`: Update game attributes
- `end_game(game_id, winner_id, final_pot)`: End a game and record results

### PlayerRepository
Handles player-related database operations.

#### Methods:
- `create(name)`: Create new player
- `get_by_id(player_id)`: Retrieve player by ID
- `get_by_name(name)`: Retrieve player by name
- `get_all()`: Get all players
- `update_stats(player_id, game_stats)`: Update player statistics

### RoundRepository
Manages poker round records.

#### Methods:
- `create(game_id, round_number)`: Create new round
- `get_by_id(round_id)`: Retrieve round by ID
- `get_game_rounds(game_id)`: Get all rounds for a game
- `end_round(round_id, winning_hand, side_pots)`: End a round and record results

### RoundActionRepository
Tracks player actions during rounds.

#### Methods:
- `create(round_id, association_id, action_type, amount=0, confidence_score=None, decision_factors=None)`: Record player action
- `get_round_actions(round_id)`: Get all actions for a round

### ChatMessageRepository
Manages in-game chat messages.

#### Methods:
- `create(game_id, player_id, message)`: Create new chat message
- `get_game_messages(game_id)`: Get all messages for a game

### GameSnapshotRepository
Handles game state snapshots.

#### Methods:
- `create(game_id, round_id, game_state)`: Create new game snapshot
- `get_game_snapshots(game_id)`: Get all snapshots for a game
- `get_round_snapshot(round_id)`: Get snapshot for specific round

## Example Usage
```python
# Create repositories with database session
game_repo = GameRepository(session)
player_repo = PlayerRepository(session)

# Create new game
game = game_repo.create(
    small_blind=10,
    big_blind=20,
    ante=5
)

# Record player action
action_repo = RoundActionRepository(session)
action_repo.create(
    round_id=1,
    association_id=1,
    action_type="raise",
    amount=100
)
``` 