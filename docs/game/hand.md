# Hand Module Documentation

## Overview
The Hand module represents and manages poker hands, providing comparison and evaluation capabilities.

## Classes

### Hand
Represents a poker hand with comparison capabilities.

#### Attributes:
- `cards`: List of Card objects
- `_rank`: Cached evaluation result

#### Methods:

##### __init__(cards=None)
Initialize a new hand, optionally with starting cards.

##### __lt__(other), __gt__(other), __eq__(other)
Comparison operators for hand ranking.

##### add_cards(cards)
Add cards to the hand.

##### show()
Get string representation of the hand.

##### evaluate()
Get formatted evaluation details.

#### Example:
```python
hand = Hand()
hand.add_cards([Card("A", "Spades"), Card("K", "Spades")])
print(hand.show())
```

#### Implementation Details:
- Caches hand evaluations for performance
- Provides rich comparison operations
- Supports detailed hand descriptions 