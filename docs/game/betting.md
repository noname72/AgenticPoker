# Betting Module Documentation

## Overview
The betting module handles all betting-related operations in the poker game, including managing betting rounds, determining valid actions, and tracking pot sizes.

## Key Functions

### betting_round(players, pot, start_index=0)
Executes a complete betting round and returns the final pot amount.

#### Parameters:
- `players` (List[Player]): List of players in the game
- `pot` (int): Current pot amount
- `start_index` (int): Starting player position (default 0)

#### Returns:
- `int`: Final pot amount after betting round

#### Example:
```python
final_pot = betting_round(players, current_pot, dealer_position)
```

### decide_action(player, current_bet, raised)
Determines a player's next action in the betting round.

#### Parameters:
- `player` (Player): Player whose action is being determined
- `current_bet` (int): Current bet amount to match
- `raised` (bool): Whether there has been a raise

#### Returns:
- `str`: Action string ("fold", "call", or "raise {amount}")

### log_action(player, action, amount=0, current_bet=0, pot=0)
Logs player actions to the game log.

#### Parameters:
- `player` (Player): The player taking the action
- `action` (str): Action type
- `amount` (int): Bet amount (optional)
- `current_bet` (int): Current bet to call (optional)
- `pot` (int): Current pot size (optional) 