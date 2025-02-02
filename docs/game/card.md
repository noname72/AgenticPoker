# Card Module Documentation

## Overview
The Card module provides a fundamental representation of playing cards in the poker game system. Each card has a rank and suit, with string representation capabilities for game display and logging.

## Card Class

### Attributes
- `rank` (str): The card's rank value
  - Valid ranks: '2' through '10', 'J', 'Q', 'K', 'A'
- `suit` (str): The card's suit
  - Valid suits: 'Clubs', 'Diamonds', 'Hearts', 'Spades'

### Methods

#### __init__(rank: str, suit: str)
Initializes a new card with the specified rank and suit.

```python
# Create a new card
ace_spades = Card("A", "Spades")
ten_hearts = Card("10", "Hearts")
```

#### __repr__() -> str
Returns a string representation of the card in the format "rank of suit".

```python
card = Card("K", "Hearts")
print(card)  # Output: K of Hearts
```

## Usage Examples

### Creating Cards
```python
# Create various cards
ace = Card("A", "Spades")
king = Card("K", "Hearts")
ten = Card("10", "Diamonds")
two = Card("2", "Clubs")
```

### Using in Collections
```python
# Create a hand of cards
hand = [
    Card("A", "Spades"),
    Card("K", "Spades"),
    Card("Q", "Spades"),
    Card("J", "Spades"),
    Card("10", "Spades")
]

# Print the hand
for card in hand:
    print(card)
```

### String Representation
```python
card = Card("Q", "Hearts")
print(f"Your card is: {card}")  # Output: Your card is: Q of Hearts
```

## Best Practices

### Card Creation
- Always use valid rank and suit values
- Use string values for both rank and suit
- Create new Card instances for each unique card

### Card Comparison
- Use string comparison for rank and suit checks
- Remember that string representation is standardized

### Memory Management
- Cards are lightweight objects
- Safe to create and destroy as needed
- No cleanup required

## Implementation Notes

1. **Simplicity**: The Card class is intentionally minimal, focusing on core functionality
2. **Immutability**: Rank and suit values should not change after creation
3. **String Representation**: Consistent format for logging and display
4. **Memory Efficiency**: Small memory footprint per card instance

## Common Operations

### Card Display
```python
# Single card
card = Card("A", "Spades")
print(card)  # A of Spades

# Multiple cards
cards = [Card("K", "Hearts"), Card("Q", "Diamonds")]
print(", ".join(str(c) for c in cards))  # K of Hearts, Q of Diamonds
```

### Card Attributes
```python
card = Card("J", "Clubs")
print(f"Rank: {card.rank}")  # Rank: J
print(f"Suit: {card.suit}")  # Suit: Clubs
```

## Related Components

The Card class is used by several other components in the poker system:
- Deck: Manages collections of cards
- Hand: Represents player card combinations
- Game: Uses cards for dealing and gameplay
- Evaluator: Analyzes card combinations for hand ranking

## Future Considerations

Potential enhancements could include:
1. Card comparison methods
2. Suit/rank validation
3. Unicode suit symbols
4. Card serialization
5. Card image representation

These would be implemented based on system needs while maintaining the current simple and efficient design. 