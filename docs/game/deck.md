# Deck Module Documentation

## Overview
The Deck module manages a standard 52-card playing deck with comprehensive tracking of dealt and discarded cards. It provides functionality for shuffling, dealing, and managing card state throughout the game.

## Deck Class

### Class Attributes
- `ranks`: List of card ranks (`[2-10, "J", "Q", "K", "A"]`)
- `suits`: List of card suits using Unicode symbols (`["♣", "♦", "♥", "♠"]`)

### Instance Attributes
- `cards`: List of remaining cards in the deck
- `dealt_cards`: List tracking cards that have been dealt
- `discarded_cards`: List tracking discarded cards
- `last_action`: String tracking the most recent deck operation

### Methods

#### __init__()
Creates a new deck with all 52 cards.

```python
deck = Deck()  # Creates fresh deck with all cards
```

#### shuffle() -> None
Shuffles the current deck and resets tracking if it's a fresh deck.

```python
deck.shuffle()  # Randomizes card order
```

#### deal(num: int = 1) -> List[Card]
Deals specified number of cards from the deck.

```python
# Deal a 5-card hand
hand = deck.deal(5)

# Deal a single card
card = deck.deal()[0]
```

#### add_discarded(cards: List[Card]) -> None
Adds cards to the discard pile.

```python
deck.add_discarded([card1, card2])  # Track discarded cards
```

#### reshuffle_discards() -> None
Shuffles discarded cards back into the deck.

```python
deck.reshuffle_discards()  # Reuse discarded cards
```

#### reshuffle_all() -> None
Reshuffles ALL cards (including dealt and discarded) back into deck.

```python
deck.reshuffle_all()  # Reset deck to initial state
```

#### remaining() -> int
Returns number of cards remaining in deck.

```python
cards_left = deck.remaining()
```

#### needs_reshuffle(needed_cards: int) -> bool
Checks if deck needs reshuffling based on needed cards.

```python
if deck.needs_reshuffle(5):
    deck.reshuffle_all()
```

#### get_state() -> DeckState
Returns current state of the deck.

```python
state = deck.get_state()
print(f"Cards remaining: {state.cards_remaining}")
```

## State Management

### DeckState Class
Represents the current state of the deck:
- `cards_remaining`: Number of cards in deck
- `cards_dealt`: Number of dealt cards
- `cards_discarded`: Number of discarded cards
- `needs_shuffle`: Whether deck needs reshuffling
- `last_action`: Most recent deck operation

### Tracking Features
- Maintains separate lists for deck, dealt, and discarded cards
- Logs all major deck operations
- Provides state validation and error checking
- Supports automatic reshuffling when needed

## Error Handling

The deck implements comprehensive error checking:
- Validates card availability before dealing
- Logs shuffle and deal operations
- Provides clear error messages
- Handles edge cases (empty deck, insufficient cards)

### Example Error Handling
```python
try:
    cards = deck.deal(10)
except ValueError as e:
    # Handle insufficient cards error
    print(f"Error: {e}")
```

## Logging

The module uses DeckLogger for operation tracking:

### Key Logging Points
- Shuffle operations
- Deal operations
- Reshuffle events
- Error conditions

### Example Log Output
```
[Deck] Shuffling deck with 32 cards remaining
[Deck] Error: Attempted to deal 5 cards with only 2 remaining
[Deck] Reshuffling all cards back into deck
```

## Best Practices

### Deck Management
1. **State Tracking**
   - Monitor card counts
   - Check for reshuffle needs
   - Track deck operations

2. **Error Prevention**
   - Validate deal amounts
   - Handle insufficient cards
   - Maintain deck integrity

3. **Performance**
   - Efficient card tracking
   - Optimized shuffling
   - Minimal state updates

4. **Memory Management**
   - Clear tracking lists when appropriate
   - Maintain references properly
   - Clean up after operations

## Implementation Notes

1. **Unicode Suits**: Uses Unicode symbols for better readability
2. **State Tracking**: Comprehensive tracking of all card movements
3. **Error Handling**: Robust validation and error reporting
4. **Logging**: Detailed operation logging for debugging
5. **Performance**: Efficient list operations for card management

## Related Components

The Deck class interacts with:
- Card: Basic card representation
- Game: Main game flow control
- Hand: Player hand management
- DeckLogger: Operation logging
- DeckState: State representation

## Future Considerations

Potential enhancements:
1. Card validation on input
2. Multiple deck support
3. Custom deck compositions
4. Serialization support
5. Performance optimizations 