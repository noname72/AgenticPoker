# Betting Module Documentation

## Overview
The betting module handles all betting-related operations in the poker game, including managing betting rounds, determining valid actions, tracking pot sizes, and handling side pots.

## Key Functions

### betting_round(players, pot, start_index=0)
Executes a complete betting round and returns the final pot amount and any side pots.

#### Parameters:
- `players` (List[Player]): List of players in the game
- `pot` (int): Current pot amount
- `start_index` (int): Starting player position (default 0)

#### Returns:
- `Tuple[int, Optional[List[Dict]]]`: Tuple containing:
  - Final pot amount after betting round
  - List of side pots (if any), where each side pot is a dict with:
    - `amount`: Size of this side pot
    - `eligible_players`: List of player names eligible for this pot

#### Example:
```python
pot_amount, side_pots = betting_round(players, current_pot, dealer_position)
```

### _calculate_side_pots(round_bets)
Calculates side pots based on player bet amounts.

#### Parameters:
- `round_bets` (Dict[Player, int]): Dictionary mapping players to their total bets

#### Returns:
- `List[Dict]`: List of side pot dictionaries, each containing:
  - `amount`: Size of this side pot
  - `eligible_players`: List of player names eligible for this pot

#### Example:
```python
side_pots = _calculate_side_pots({
    player_a: 100,  # all-in
    player_b: 200,  # all-in
    player_c: 300   # active
})
# Returns: [
#   {"amount": 300, "eligible_players": ["A", "B", "C"]},
#   {"amount": 300, "eligible_players": ["B", "C"]},
#   {"amount": 300, "eligible_players": ["C"]}
# ]
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