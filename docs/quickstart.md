# Quickstart Guide

## Overview
This guide will help you quickly set up and run your first AI poker game. The system simulates 5-card draw poker games between AI players powered by language models, with configurable strategies and personalities.

## Installation

1. Clone the repository and install dependencies:
```bash
git clone <repository-url>
cd poker-ai
pip install -r requirements.txt
```

2. Set up your environment variables:
```bash
# Create .env file with your API key
echo "OPENAI_API_KEY=your_key_here" > .env
```

## Basic Usage

### Running a Simple Game
The quickest way to start a game is using the default configuration:

```python
from datetime import datetime
from game import AgenticPoker, GameConfig
from agents.agent import Agent
from agents.random_agent import RandomAgent

# Generate unique session ID
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# Create AI players with different strategies
players = [
    Agent(
        "Alice", 
        chips=1000, 
        strategy_style="Aggressive Bluffer",
        use_reasoning=True,
        use_reflection=True,
        use_planning=True,
        use_opponent_modeling=True,
        session_id=session_id,
        communication_style="Intimidating"
    ),
    Agent(
        "Bob", 
        chips=1000, 
        strategy_style="Calculated and Cautious",
        use_planning=True,
        session_id=session_id,
        communication_style="Analytical"
    ),
    RandomAgent(  # Add a random baseline player
        "Randy",
        chips=1000
    )
]

# Initialize game with GameConfig
game = AgenticPoker(
    players,
    config=GameConfig(
        starting_chips=1000,
        small_blind=50,
        big_blind=100,
        ante=10,
        session_id=session_id,
        max_raise_multiplier=3,  # Maximum raise can be 3x the current bet
        max_raises_per_round=4,  # Limit number of raises per betting round
        min_bet=100,  # Minimum bet equal to big blind
    )
)

# Start the game
game.play_game()
```

### Game Configuration
Use GameConfig for detailed game setup:

```python
config = GameConfig(
    starting_chips=1000,    # Initial chips for each player
    small_blind=50,         # Small blind amount
    big_blind=100,          # Big blind amount
    ante=10,               # Ante amount (optional)
    max_rounds=None,        # Optional limit on number of rounds
    session_id=session_id,  # For logging and memory management
    max_raise_multiplier=3, # Maximum raise as multiplier of current bet
    max_raises_per_round=4, # Maximum raises allowed per betting round
    min_bet=100            # Minimum bet amount (defaults to big blind)
)
```

### Configuring AI Players
You can customize AI players with different features:

```python
player = Agent(
    name="Alice",
    chips=1000,
    strategy_style="Aggressive Bluffer",
    use_reasoning=True,     # Enable detailed decision reasoning
    use_reflection=True,    # Enable learning from past hands
    use_planning=True,      # Enable multi-step planning
    use_opponent_modeling=True,  # Enable opponent behavior analysis
    use_reward_learning=True,    # Enable reward-based learning
    learning_rate=0.1,          # Learning rate for reward updates
    communication_style="Intimidating",  # Communication approach
    session_id=session_id       # For memory persistence
)
```

### Available Strategy Styles
- "Aggressive Bluffer"
- "Calculated and Cautious"
- "Chaotic and Unpredictable"

### Communication Styles
- "Intimidating"
- "Analytical"
- "Friendly"

### Game State and Memory Management
The game automatically manages state and memory:

```python
# Access current game state
game_state = game.get_state()

# Memory is automatically managed for each agent
# Each agent gets a session-specific ChromaDB collection:
collection_name = f"agent_{name.lower().replace(' ', '_')}_{session_id}_memory"
```

### Logging Configuration
The game automatically sets up logging with the session ID:

```python
from util import setup_logging

# Set up logging with session ID
setup_logging(session_id)

# Configure specific loggers
from loggers.config import configure_loggers
import logging

configure_loggers({
    "betting": logging.INFO,
    "llm": logging.INFO,  # Set to DEBUG to see prompts/responses
    "table": logging.INFO,
})
```

## Common Patterns

### Analyzing Game Results
```python
# After game completion
for player in game.players:
    print(f"{player.name}:")
    print(f"  Final chips: ${player.chips}")
    if hasattr(player, "strategy_planner"):
        print(f"  Current strategy: {player.strategy_planner.current_plan}")
```

### Monitoring Agent Learning
```python
# Check agent state and decisions
if hasattr(player, "opponent_stats"):
    print(f"Opponent analysis: {player.opponent_stats}")
if hasattr(player, "strategy_planner"):
    print(f"Current plan: {player.strategy_planner.current_plan}")
```

## Next Steps
- Review the detailed module documentation in `docs/`
- Explore advanced AI configurations in `docs/llm_agent.md`
- Learn about game analysis tools in `docs/analysis.md`

## Troubleshooting
- Ensure your OpenAI API key is properly set in `.env`
- Check logs in the `logs/` directory for detailed error information
- Verify ChromaDB is working properly for memory persistence
- Review the error handling section in `docs/llm_agent.md`
