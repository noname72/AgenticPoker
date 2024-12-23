# Quickstart Guide

## Overview
This guide will help you quickly set up and run your first AI poker game. The system simulates poker games between AI players powered by language models, with configurable strategies and personalities.

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
from game import AgenticPoker
from agents.llm_agent import LLMAgent

# Create AI players with different strategies
players = [
    LLMAgent("Alice", chips=1000, strategy_style="Aggressive Bluffer"),
    LLMAgent("Bob", chips=1000, strategy_style="Calculated and Cautious"),
    LLMAgent("Charlie", chips=1000, strategy_style="Chaotic and Unpredictable")
]

# Initialize and start the game
game = AgenticPoker(
    players,
    starting_chips=1000,
    small_blind=10,
    big_blind=20,
    ante=0
)

game.start_game()
```

### Configuring AI Players
You can customize AI players with different features:

```python
player = LLMAgent(
    name="Alice",
    chips=1000,
    strategy_style="Aggressive Bluffer",
    use_reasoning=True,     # Enable detailed decision reasoning
    use_reflection=True,    # Enable learning from past hands
    use_planning=True,      # Enable multi-step planning
    use_opponent_modeling=True,  # Enable opponent behavior analysis
    use_reward_learning=True,    # Enable reward-based learning
    learning_rate=0.1           # Learning rate for reward updates
)
```

### Available Strategy Styles
- "Aggressive Bluffer"
- "Calculated and Cautious"
- "Chaotic and Unpredictable"
- "Tight and Aggressive"
- "Loose and Passive"

### Reward Learning Configuration
Enable reward-based learning for adaptive gameplay:

```python
# Create agent with reward learning
learning_agent = LLMAgent(
    "Alice",
    chips=1000,
    strategy_style="Aggressive Bluffer",
    use_reward_learning=True,
    learning_rate=0.1
)

# Update agent based on game outcomes
learning_agent.update_from_reward(
    reward=100,  # Positive reward for winning
    game_state={
        "all_in": True,
        "bluff_successful": True,
        "position": "dealer"
    }
)
```

## Game Configuration

### Basic Settings
```python
game = AgenticPoker(
    players,
    starting_chips=1000,  # Starting chips for each player
    small_blind=10,       # Small blind amount
    big_blind=20,        # Big blind amount
    ante=5,              # Ante amount (optional)
    max_rounds=100       # Maximum number of rounds (optional)
)
```

### Logging Configuration
The game provides detailed logging of all actions:

```python
import logging

# Set up logging with session ID
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
logging.basicConfig(
    level=logging.INFO,
    filename=f"logs/game_{session_id}.log",
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

## Database Integration

### Setting Up the Database
```python
from data.model import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create database engine
engine = create_engine('sqlite:///poker_game.db')
Base.metadata.create_all(engine)

# Create session
Session = sessionmaker(bind=engine)
session = Session()
```

### Using Repositories
```python
from data.repositories import GameRepository, PlayerRepository

# Initialize repositories
game_repo = GameRepository(session)
player_repo = PlayerRepository(session)

# Create and track game
game_record = game_repo.create(
    small_blind=10,
    big_blind=20,
    ante=5
)

# Update player statistics
player_repo.update_stats(
    player_id=1,
    game_stats={
        "won": True,
        "winnings": 500,
        "pot_size": 1000,
        "duration": 300
    }
)
```

## Common Patterns

### Handling Game Events
```python
# Listen for specific game events
@game.on_round_start
def handle_round_start(round_number):
    logging.info(f"Round {round_number} started")

@game.on_player_action
def handle_player_action(player, action, amount):
    logging.info(f"{player.name} {action} {amount}")
```

### Analyzing Game Results
```python
# After game completion
for player in game.players:
    print(f"{player.name}:")
    print(f"  Final chips: ${player.chips}")
    print(f"  Hands won: {player.stats.hands_won}")
    print(f"  Largest pot: ${player.stats.largest_pot}")
```

### Analyzing Learning Progress
```python
# Check action values after learning
print(f"Action Values: {player.action_values}")
print(f"Recent Rewards: {[r for _, _, r in player.action_history[-5:]]}")

# Monitor personality trait changes
print(f"Current Traits: {player.personality_traits}")
```

## Next Steps
- Review the detailed module documentation in `docs/`
- Explore advanced AI configurations in `docs/llm_agent.md`
- Check out example strategies in `examples/`
- Learn about game analysis tools in `docs/analysis.md`

## Troubleshooting
- Ensure your OpenAI API key is properly set
- Check logs in the `logs/` directory for detailed error information
- Verify database connectivity if using persistence
- Consult the full documentation for specific error messages 