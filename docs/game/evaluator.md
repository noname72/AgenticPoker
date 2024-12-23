# Evaluator Module Documentation

## Overview
The Evaluator module handles poker hand evaluation, determining hand rankings and comparing hands against each other.

## Functions

### evaluate_hand(cards)
Evaluates a 5-card poker hand and returns its ranking information.

#### Parameters:
- `cards` (List[Card]): List of 5 Card objects

#### Returns:
- `Tuple[int, List[int], str]`: Contains:
  - Hand rank (1-10, lower is better)
  - Tiebreaker values
  - Human-readable description

#### Hand Rankings:
1. Royal Flush
2. Straight Flush
3. Four of a Kind
4. Full House
5. Flush
6. Straight
7. Three of a Kind
8. Two Pair
9. One Pair
10. High Card

#### Example:
```python
rank, tiebreakers, description = evaluate_hand(cards)
print(description)  # "Full House, Kings over Tens"
```

#### Implementation Details:
- Handles special cases like Ace-low straights
- Provides detailed tiebreakers for identical hand types
- Returns human-readable descriptions of hands 