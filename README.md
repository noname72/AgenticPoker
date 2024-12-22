# AI Poker Game

A poker game simulation featuring AI players powered by LLMs (Language Learning Models).

## Features

- 5-card draw poker implementation
- AI players with different strategies and personalities
- Natural language communication between players
- Configurable game parameters (blinds, starting chips, antes, etc.)
- Detailed logging of game progress and player interactions
- Side pot handling for all-in situations
- Session-based logging with unique IDs

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your_key_here" > .env
```

3. Run the game:
```bash
python main.py
```

## Architecture

- `game/` - Core poker game implementation
  - `game.py` - Main game logic and flow control
  - `player.py` - Player state and action management
  - `hand.py` - Poker hand evaluation
  - `deck.py` - Card deck management
  - `betting.py` - Betting round mechanics
- `poker_agents.py` - AI player implementation using LLMs
- `main.py` - Game runner
- `util.py` - Utility functions and logging setup

## Customization

You can modify player strategies and game parameters in main.py:

```python
players = [
    AIPlayer("Alice", chips=1000, strategy_style="Aggressive Bluffer"),
    AIPlayer("Bob", chips=1000, strategy_style="Calculated and Cautious"),
    AIPlayer("Charlie", chips=1000, strategy_style="Chaotic and Unpredictable"),
    AIPlayer("Dana", chips=1000, strategy_style="Aggressive Bluffer")
]

game = PokerGame(
    players,
    starting_chips=1000,
    small_blind=50,
    big_blind=100,
    ante=10,
    session_id=None  # Optional: Provide custom session ID
)
```

### Available Strategy Styles
- "Aggressive Bluffer" - High aggression and bluff frequency
- "Calculated and Cautious" - Conservative play style
- "Chaotic and Unpredictable" - Mixed strategy with random elements

## Testing

Run the test suite:
```bash
pytest tests/
```

For coverage report:
```bash
pytest tests/ --cov=./ --cov-report=xml
```

## Logging

The game generates detailed logs including:
- Game configuration and setup
- Player actions and decisions
- Betting rounds and pot management
- Hand evaluations and showdowns
- Player eliminations and game outcomes

Logs are written to both console and `poker_game.log` file.
