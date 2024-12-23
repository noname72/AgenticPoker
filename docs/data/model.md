# Database Model Documentation

## Overview
The Model module defines the SQLAlchemy ORM models representing the poker game's database schema.

## Models

### Game
Represents a poker game instance.

#### Attributes:
- `id`: Primary key
- `session_id`: External reference ID
- `small_blind`, `big_blind`, `ante`: Game betting parameters
- `pot`: Current pot amount
- `created_at`, `updated_at`: Timestamps
- `duration`: Game duration in seconds
- `total_hands`: Number of hands played
- `winner_id`: Foreign key to winning player
- `final_pot`: Final pot amount

### Player
Represents a poker player.

#### Attributes:
- `id`: Primary key
- `name`: Unique username
- `created_at`: Account creation timestamp
- `stats`: Relationship to PlayerStats

### GamePlayerAssociation
Links players to games with game-specific state.

#### Attributes:
- `game_id`, `player_id`: Foreign keys
- `chips`: Current chip count
- `folded`: Fold status
- `bet`: Current bet amount
- `current_hand`: Serialized hand data

### Round
Represents a betting round.

#### Attributes:
- `id`: Primary key
- `game_id`: Foreign key to game
- `round_number`: Sequential round number
- `pot`: Round pot amount
- `started_at`, `ended_at`: Timestamps
- `winning_hand`: Winning hand description
- `side_pots`: JSON structure for side pots

### RoundAction
Records player actions during rounds.

#### Attributes:
- `id`: Primary key
- `round_id`, `association_id`: Foreign keys
- `action_type`: Type of action
- `amount`: Bet amount
- `timestamp`: Action timestamp
- `confidence_score`: AI confidence metric
- `decision_factors`: AI decision details

### ChatMessage
Stores in-game chat messages.

#### Attributes:
- `id`: Primary key
- `game_id`, `player_id`: Foreign keys
- `message`: Message content
- `timestamp`: Message timestamp

### GameSnapshot
Captures game state for replay/analysis.

#### Attributes:
- `id`: Primary key
- `game_id`, `round_id`: Foreign keys
- `timestamp`: Snapshot timestamp
- `game_state`: Complete game state as JSON

### PlayerStats
Tracks player performance statistics.

#### Attributes:
- `id`: Primary key
- `player_id`: Foreign key to player
- `games_played`: Total games
- `hands_won`: Total hands won
- `total_winnings`: Cumulative winnings
- `bluff_success_rate`: Bluffing statistics
- `avg_bet_size`: Average betting amount

## Relationships
- Game → Rounds: one-to-many
- Game ↔ Players: many-to-many through GamePlayerAssociation
- Round → Actions: one-to-many
- Player → Stats: one-to-one

## Example Usage
```python
# Create new game record
game = Game(
    small_blind=10,
    big_blind=20,
    ante=5,
    game_type="5-card-draw"
)

# Record player action
action = RoundAction(
    round_id=1,
    association_id=1,
    action_type="raise",
    amount=100,
    confidence_score=0.85
)
``` 