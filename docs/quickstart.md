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
from datetime import datetime

# Generate unique session ID
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# Create AI players with different strategies
players = [
    LLMAgent(
        "Alice", 
        chips=1000, 
        strategy_style="Aggressive Bluffer",
        session_id=session_id
    ),
    LLMAgent(
        "Bob", 
        chips=1000, 
        strategy_style="Calculated and Cautious",
        session_id=session_id
    ),
    LLMAgent(
        "Charlie", 
        chips=1000, 
        strategy_style="Chaotic and Unpredictable",
        session_id=session_id
    )
]

# Initialize and start the game
game = AgenticPoker(
    players,
    starting_chips=1000,
    small_blind=50,
    big_blind=100,
    ante=10,
    session_id=session_id
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

### Reward Learning Configuration
Enable reward-based learning for adaptive gameplay:

```python
# Create agent with reward learning
learning_agent = LLMAgent(
    "Alice",
    chips=1000,
    strategy_style="Aggressive Bluffer",
    use_reward_learning=True,
    learning_rate=0.1,
    session_id=session_id
)

# Personality traits are automatically adjusted based on outcomes
print(f"Initial traits: {learning_agent.personality_traits}")
# {'aggression': 0.5, 'bluff_frequency': 0.5, 'risk_tolerance': 0.5}
```

## Game Configuration

### Basic Settings
```python
game = AgenticPoker(
    players,
    starting_chips=1000,  # Starting chips for each player
    small_blind=50,       # Small blind amount
    big_blind=100,        # Big blind amount
    ante=10,             # Ante amount
    session_id=session_id # For logging and memory management
)
```

### Logging Configuration
The game automatically sets up logging with the session ID:

```python
from util import setup_logging

# Set up logging with session ID
setup_logging(session_id)
```

## Memory Management

### Using ChromaDB for Persistent Memory
The LLM Agent automatically manages memory using ChromaDB:

```python
# Memory is initialized with session-specific collection
collection_name = f"agent_{name.lower().replace(' ', '_')}_{session_id}_memory"
memory_store = ChromaMemoryStore(collection_name)

# Memory is automatically used for decision making
relevant_memories = memory_store.get_relevant_memories(
    query=game_state,
    k=2
)
```

## Common Patterns

### Analyzing Game Results
```python
# After game completion
for player in game.players:
    print(f"{player.name}:")
    print(f"  Final chips: ${player.chips}")
```

### Monitoring Agent Learning
```python
# Check action probabilities
print(f"Action probabilities: {player._get_action_probabilities()}")

# Monitor personality trait changes
print(f"Current traits: {player.personality_traits}")
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