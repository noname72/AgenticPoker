# AI Poker Simulation Library

This library simulates a poker game with AI players powered by LLMs (Language Learning Models), incorporating realistic game mechanics such as blinds, antes, side pots, and bankroll management. It provides a modular structure, making it easy to extend and customize for different poker variants.

---

## Features

1. **AI Players**
   - LLM-powered poker agents with distinct personalities and strategies
   - Configurable strategy styles (Aggressive, Cautious, Chaotic)
   - Natural language communication between players
   - Adaptive learning from game outcomes

2. **Deck and Card Management**
   - Standard 52-card deck
   - Supports shuffling and dealing cards

3. **Player Actions**
   - Players can place bets, fold, and participate in betting rounds
   - Supports bankroll management to track player chips across hands
   - AI decision-making with configurable risk tolerance

4. **Betting Mechanics**
   - Implements small and big blinds
   - Optional antes
   - Supports side pots for "all-in" scenarios
   - Dynamic blind adjustment based on player chip stacks

5. **Hand Evaluation**
   - Evaluates hands based on standard poker rankings
   - Provides descriptive output for hand rankings
   - Detailed logging of hand evaluations and decisions

6. **Game Flow**
   - Handles pre-draw and post-draw betting rounds
   - Distributes winnings based on hand rankings and side pots
   - Eliminates players who run out of chips
   - Comprehensive game state tracking and logging

7. **Customization**
   - Configurable blinds and starting chip amounts
   - Extensible to other poker variants
   - Adjustable AI personality traits and strategy styles

---

## Installation

1. Clone the repository and install dependencies:

```bash
# Clone the repository
git clone <repository-url>

# Navigate to the library directory
cd poker-simulation-library

# Install required packages
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your_key_here" > .env
```

---

## Module Descriptions

// ... existing module descriptions ...

### `poker_agents.py`
Implements AI poker players using language models.

```python
class PokerAgent:
    def __init__(self, name, model_type="gpt", strategy_style="Aggressive Bluffer"):
        self.name = name
        self.model_type = model_type
        self.strategy_style = strategy_style
        # ... initialization code ...

    def decide_action(self, game_state):
        """Use LLM to decide next poker action."""
        pass

    def interpret_message(self, message):
        """Analyze and respond to table talk."""
        pass
```

---

## Example Usage

```python
from game import PokerGame
from poker_agents import PokerAgent

# Create AI players with different strategies
players = [
    PokerAgent("Alice", strategy_style="Aggressive Bluffer"),
    PokerAgent("Bob", strategy_style="Calculated and Cautious"),
    PokerAgent("Charlie", strategy_style="Chaotic and Unpredictable")
]

# Initialize and start the game
game = PokerGame(players, starting_chips=1000, small_blind=10, big_blind=20)
game.start_game()
```

---

## Testing

Run the test suite:

```bash
pytest tests/
```

For coverage report:

```bash
pytest tests/ --cov=./ --cov-report=xml
```
