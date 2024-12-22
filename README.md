# AI Poker Game

A poker game simulation featuring AI players powered by LLMs (Language Learning Models).

## Features

- 5-card draw poker implementation
- AI players with different strategies and personalities
- Natural language communication between players
- Configurable game parameters (blinds, starting chips, etc.)
- Detailed logging of game progress

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
- `poker_agents.py` - AI player implementation using LLMs
- `main.py` - Game runner
- `util.py` - Utility functions

## Customization

You can modify player strategies and game parameters in main.py:

```python
players = [
    AIPlayer("Alice", chips=1000, strategy_style="Aggressive Bluffer"),
    AIPlayer("Bob", chips=1000, strategy_style="Calculated and Cautious"),
    AIPlayer("Charlie", chips=1000, strategy_style="Chaotic and Unpredictable"),
    AIPlayer("Dana", chips=1000, strategy_style="Aggressive Bluffer")
]

game = PokerGame(players, starting_chips=1000, small_blind=50, big_blind=100)
```
