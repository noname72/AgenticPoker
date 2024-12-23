# Deck Module Documentation

## Overview
The Deck module manages a standard 52-card playing deck, providing functionality for shuffling and dealing cards.

## Classes

### Deck
Represents a standard deck of 52 playing cards.

#### Class Attributes:
- `ranks`: List of card ranks (2-10, J, Q, K, A)
- `suits`: List of card suits (Clubs, Diamonds, Hearts, Spades)

#### Methods:
- `__init__()`: Creates a new deck with all 52 cards
- `shuffle()`: Randomly shuffles the deck
- `deal(num=1)`: Deals specified number of cards from the deck

#### Example:
```python
deck = Deck()
deck.shuffle()
hand = deck.deal(5)  # Deal 5 cards
```

#### Implementation Details:
- Automatically creates all 52 combinations of ranks and suits
- Uses random.shuffle for randomization
- Keeps track of remaining cards after dealing 