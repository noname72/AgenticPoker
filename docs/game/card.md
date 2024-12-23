# Card Module Documentation

## Overview
The Card module provides a basic representation of playing cards with rank and suit attributes.

## Classes

### Card
Represents a single playing card with a rank and suit.

#### Attributes:
- `rank`: The card's rank (2-10, J, Q, K, A)
- `suit`: The card's suit (Clubs, Diamonds, Hearts, Spades)

#### Methods:
- `__init__(rank, suit)`: Initialize a new card
- `__repr__()`: String representation of the card

#### Example:
```python
ace_spades = Card("A", "Spades")
print(ace_spades)  # Output: A of Spades
``` 