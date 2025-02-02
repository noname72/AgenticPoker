# Hand Module Documentation

## Overview
The Hand module provides a comprehensive representation of poker hands with evaluation, comparison, and state management capabilities. It integrates with the evaluator module for hand ranking and supports detailed state tracking.

## Hand Class

### Attributes
- `cards` (List[Card]): List of cards in the hand
- `_rank` (Optional[tuple]): Cached evaluation result containing:
  - Rank value
  - Tiebreaker values
  - Description

### Methods

#### __init__(cards: Optional[List[Card]] = None)
Initializes a new hand, optionally with starting cards.

```python
# Create empty hand
hand = Hand()

# Create hand with cards
hand = Hand([
    Card("A", "♠"),
    Card("K", "♠"),
    Card("Q", "♠"),
    Card("J", "♠"),
    Card("10", "♠")
])
```

#### Comparison Methods

##### __lt__(other: Hand) -> bool, __gt__(other: Hand) -> bool, __eq__(other: Hand) -> bool
Support rich comparison operations between hands.

```python
hand1 = Hand([...])  # Royal Flush
hand2 = Hand([...])  # Full House
print(hand1 > hand2)  # True
print(hand2 < hand1)  # True
print(hand1 == hand2)  # False
```

#### Card Management

##### add_cards(cards: List[Card]) -> None
Add cards to the hand and invalidate cached rank.

```python
hand = Hand()
hand.add_cards([Card("A", "♠"), Card("K", "♠")])
```

##### remove_cards(positions: List[int]) -> None
Remove cards by position indices (highest first).

```python
hand.remove_cards([1, 3])  # Remove cards at indices 1 and 3
```

#### Evaluation and Display

##### evaluate() -> Tuple[int, List[int], str]
Evaluate the current hand and return ranking information.

```python
rank, tiebreakers, description = hand.evaluate()
print(description)  # e.g., "Royal Flush"
print(tiebreakers)  # e.g., [14, 13, 12, 11, 10]
```

##### show() -> str
Get detailed string representation of the hand.

```python
print(hand.show())
# Output example:
# A of ♠, K of ♠, Q of ♠, J of ♠, 10 of ♠
#     - Royal Flush [Rank: 1, Tiebreakers: [14, 13, 12, 11, 10]]
```

#### State Management

##### get_state() -> HandState
Get current state of the hand including evaluation details.

```python
state = hand.get_state()
print(state.cards)        # List of card strings
print(state.rank)         # Hand rank description
print(state.rank_value)   # Numerical rank value
print(state.tiebreakers)  # Tiebreaker values
print(state.is_evaluated) # Whether hand has been evaluated
```

##### compare_to(other: Hand) -> int
Compare this hand to another hand.

```python
result = hand1.compare_to(hand2)
if result > 0:
    print("Hand1 is better")
elif result < 0:
    print("Hand2 is better")
else:
    print("Hands are equal")
```

### Error Handling

The Hand class implements comprehensive error checking:

```python
try:
    # Invalid number of cards
    hand.evaluate()  # Raises ValueError if not 5 cards
    
    # Invalid card types
    hand.add_cards(["not a card"])  # Raises TypeError
    
    # None cards
    hand.add_cards(None)  # Raises TypeError
    
except (ValueError, TypeError) as e:
    print(f"Error: {e}")
```

## Implementation Notes

### Rank Caching
- Hand evaluations are cached for performance
- Cache is invalidated when cards change
- Invalid hands return infinity rank

### Comparison Logic
- Handles invalid hands gracefully
- Supports full poker hand hierarchy
- Uses tiebreakers for equal ranks

### State Validation
- Ensures correct number of cards
- Validates card objects
- Maintains evaluation consistency

## Best Practices

### 1. Hand Management
- Initialize with valid Card objects
- Check hand size before evaluation
- Clear rank cache when modifying

### 2. Error Handling
- Validate input cards
- Handle invalid hands gracefully
- Check evaluation requirements

### 3. Performance
- Use cached evaluations
- Invalidate cache appropriately
- Optimize comparisons

### 4. State Tracking
- Monitor evaluation status
- Maintain accurate card list
- Track rank information

## Related Components

The Hand class interacts with:
- Card: Basic card representation
- Evaluator: Hand evaluation logic
- HandState: State representation
- HandRank: Rank enumeration
- Game: Main game flow

## Future Considerations

1. Support for different poker variants
2. Performance optimizations
3. Extended hand statistics
4. Probability calculations
5. Hand strength analysis 