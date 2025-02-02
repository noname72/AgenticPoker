# Evaluator Module Documentation

## Overview
The Evaluator module provides comprehensive poker hand evaluation, determining hand rankings, calculating tiebreakers, and generating human-readable descriptions of poker hands.

## HandEvaluation Class

A named tuple containing the complete evaluation of a poker hand:

### Attributes
- `rank` (HandRank): The rank of the hand (HIGH_CARD to ROYAL_FLUSH)
- `tiebreakers` (List[int]): Tiebreaker values in descending order of importance
- `description` (str): Human readable description of the hand

## Core Function

### evaluate_hand(cards: List[Card]) -> HandEvaluation

Evaluates a 5-card poker hand and returns its complete evaluation.

#### Parameters
- `cards` (List[Card]): A list of exactly 5 Card objects

#### Returns
- `HandEvaluation`: Named tuple containing rank, tiebreakers, and description

#### Hand Rankings (from best to worst)
1. **Royal Flush** - A, K, Q, J, 10 of the same suit
2. **Straight Flush** - Five sequential cards of the same suit
3. **Four of a Kind** - Four cards of the same rank
4. **Full House** - Three of a kind plus a pair
5. **Flush** - Any five cards of the same suit
6. **Straight** - Five sequential cards of mixed suits
7. **Three of a Kind** - Three cards of the same rank
8. **Two Pair** - Two different pairs
9. **One Pair** - One pair of matching cards
10. **High Card** - Highest card when no other hand is made

#### Example Usage
```python
# Create a hand
hand = [
    Card('A', '♠'), 
    Card('K', '♠'), 
    Card('Q', '♠'), 
    Card('J', '♠'), 
    Card('10', '♠')
]

# Evaluate the hand
evaluation = evaluate_hand(hand)

print(evaluation.rank)        # HandRank.ROYAL_FLUSH
print(evaluation.tiebreakers) # [14, 13, 12, 11, 10]
print(evaluation.description) # "Royal Flush"
```

## Implementation Details

### Card Value Conversion
```python
values = {
    "2": 2,  "3": 3,  "4": 4,  "5": 5,
    "6": 6,  "7": 7,  "8": 8,  "9": 9,
    "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14
}
```

### Special Cases

#### Ace-Low Straight
```python
# Special case: A,2,3,4,5
if set(ranks) == {14, 2, 3, 4, 5}:
    is_straight = True
    ranks = [5, 4, 3, 2, 1]  # Ace counts as low
```

### Validation

The evaluator performs several validations:
- Exactly 5 cards required
- No duplicate cards allowed
- Valid card ranks and suits

```python
# Example validation error
try:
    evaluate_hand([card1, card2])  # Less than 5 cards
except ValueError as e:
    print(e)  # "Hand must contain exactly 5 cards"
```

## Hand Descriptions

The evaluator provides detailed hand descriptions:

```python
# Example descriptions
"Royal Flush"
"Straight Flush, 9 high"
"Four of a Kind, 8s"
"Full House, Kings over Tens"
"Flush, Ace high"
"Straight, Queen high"
"Three of a Kind, 7s"
"Two Pair, Aces and Queens"
"One Pair, Jacks"
"High Card, Ace"
```

## Tiebreaker System

Tiebreakers are provided in descending order of importance:

### Examples
1. **Four of a Kind**: [quad_rank, kicker]
2. **Full House**: [trips_rank, pair_rank]
3. **Flush**: [high_card, next_high, ...]
4. **Two Pair**: [high_pair, low_pair, kicker]
5. **One Pair**: [pair_rank, high_kicker, mid_kicker, low_kicker]

## Helper Functions

### _rank_to_name(rank: int) -> str
Converts numeric ranks to card names.

```python
names = {
    14: "Ace",
    13: "King",
    12: "Queen",
    11: "Jack",
    10: "10"
}
```

## Best Practices

1. **Input Validation**
   - Always provide exactly 5 cards
   - Ensure no duplicate cards
   - Use valid card ranks and suits

2. **Error Handling**
   - Handle ValueError for invalid hands
   - Check for proper card objects
   - Validate input before evaluation

3. **Performance**
   - Sort ranks once for multiple checks
   - Use set operations for straights
   - Cache frequency counts

4. **Usage**
   - Compare hands using rank first
   - Use tiebreakers in order
   - Parse descriptions for display

## Related Components

The Evaluator interacts with:
- Card: Basic card representation
- HandRank: Enumeration of hand rankings
- Game: Main game flow control
- Hand: Player hand management

## Future Considerations

Potential enhancements:
1. Support for different poker variants
2. Performance optimizations
3. Additional hand statistics
4. Probability calculations
5. Hand strength analysis 