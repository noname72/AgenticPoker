# Poker Simulation Library

This library simulates a poker game, incorporating realistic game mechanics such as blinds, antes, side pots, and bankroll management. It provides a modular structure, making it easy to extend and customize for different poker variants.

---

## Features

1. **Deck and Card Management**
   - Standard 52-card deck.
   - Supports shuffling and dealing cards.

2. **Player Actions**
   - Players can place bets, fold, and participate in betting rounds.
   - Supports bankroll management to track player chips across hands.

3. **Betting Mechanics**
   - Implements small and big blinds.
   - Optional antes.
   - Supports side pots for "all-in" scenarios.

4. **Hand Evaluation**
   - Evaluates hands based on standard poker rankings (e.g., Royal Flush, Full House).
   - Provides descriptive output for hand rankings.

5. **Game Flow**
   - Handles pre-draw and post-draw betting rounds.
   - Distributes winnings based on hand rankings and side pots.
   - Eliminates players who run out of chips.

6. **Customization**
   - Configurable blinds and starting chip amounts.
   - Easily extensible to other poker variants (e.g., Texas Hold'em).

---

## Installation

Clone the repository and include the modules in your Python project.

```bash
# Clone the repository
git clone <repository-url>

# Navigate to the library directory
cd poker-simulation-library
```

---

## Module Descriptions

### `card.py`
Represents individual playing cards.

```python
class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"{self.rank} of {self.suit}"
```

### `deck.py`
Handles deck creation, shuffling, and dealing.

```python
class Deck:
    def __init__(self):
        self.cards = [Card(rank, suit) for suit in ["Clubs", "Diamonds", "Hearts", "Spades"] for rank in range(2, 11) + ["J", "Q", "K", "A"]]

    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self, num=1):
        return self.cards[:num]
```

### `hand.py`
Represents a player's hand of cards.

```python
class Hand:
    def __init__(self):
        self.cards = []

    def add_cards(self, cards):
        self.cards.extend(cards)

    def show(self):
        return ", ".join(str(card) for card in self.cards)
```

### `player.py`
Manages player data, including chips, bets, and hand.

```python
class Player:
    def __init__(self, name, chips=1000):
        self.name = name
        self.chips = chips
        self.bet = 0
        self.folded = False
        self.hand = Hand()

    def place_bet(self, amount):
        if amount > self.chips:
            raise ValueError("Not enough chips!")
        self.chips -= amount
        self.bet += amount

    def fold(self):
        self.folded = True
```

### `evaluator.py`
Evaluates the strength of poker hands based on standard rankings.

```python
def evaluate_hand(cards):
    """
    Evaluate hand strength with descriptive output.
    Returns a tuple: (rank, tiebreak_info, description).
    """
    pass  # Full implementation in the library.
```

### `betting.py`
Handles betting rounds and player actions.

```python
def betting_round(players, pot, start_index=0):
    """Manage betting rounds."""
    pass

def decide_action(player, current_bet, raised):
    """Simulate or collect a player's decision."""
    pass
```

### `game.py`
Manages the overall game flow, including dealing cards, betting rounds, and resolving pots.

```python
class PokerGame:
    def __init__(self, player_names, starting_chips=1000, small_blind=10, big_blind=20):
        self.players = [Player(name, starting_chips) for name in player_names]
        self.small_blind = small_blind
        self.big_blind = big_blind

    def start_game(self):
        """Run the poker game until one player remains."""
        pass
```

---

## Example Usage

```python
from game import PokerGame

player_names = ["Alice", "Bob", "Charlie", "Dana"]
game = PokerGame(player_names, starting_chips=100, small_blind=5, big_blind=10)
game.start_game()
```