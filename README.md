# AgenticPoker

![Project Status](https://img.shields.io/badge/status-in%20development-orange)

AgenticPoker is a poker game simulation featuring AI players powered by Large Language Models (LLMs). The system simulates **5-card draw poker**, with intelligent agents capable of making strategic decisions, learning from past hands, and engaging in natural language table talk.

Designed for realism and adaptability, AgenticPoker offers a comprehensive poker experience, blending advanced AI capabilities with detailed game mechanics.

---

## Key Features

### Core Game Mechanics
- **Game Variants**: Implements 5-card draw poker with support for future variants
- **Hand Evaluation**: Accurate hand evaluation and comparison logic
- **Side Pot Management**: Handles complex all-in scenarios with pot validation
- **Customizable Parameters**: Configure blinds, antes, starting chips, and game modes
- **Session Tracking**: Unique session IDs for organized gameplay and persistence
- **Database Integration**: Complete hand history and game state tracking
- **Error Handling**: Robust error recovery and state validation

### AI Players
AgenticPoker introduces intelligent LLM-powered agents with unique personalities and advanced decision-making capabilities.

#### Decision-Making Capabilities:
- **Dynamic Strategy Adaptation**: Real-time adjustments based on gameplay
- **Memory-Based Learning**: ChromaDB-powered persistent memory system
- **Pattern Recognition**: Identifies trends in opponent behavior
- **Strategic Planning**: Multi-round planning with automatic replanning triggers

#### Personality Profiles:
Each agent embodies a distinct playing style and communication approach:
- **Playing Styles**: Aggressive, cautious, unpredictable, or balanced strategies
- **Communication Styles**: 
  - **Intimidating**: Applies psychological pressure
  - **Analytical**: Focuses on probabilities and logical observations
  - **Friendly**: Engages with light, strategic banter
- **Emotional Traits**: Adaptive emotional responses and table talk

#### Advanced Features:
- **Persistent Memory**: Session-specific ChromaDB collections for learning
- **State Validation**: Comprehensive chip counting and pot validation
- **Detailed Logging**: Complete game state and decision tracking
- **Resource Management**: Automatic cleanup and connection handling

---

## Quick Start Guide

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set Up Environment Variables
```bash
# Create .env file and add OpenAI API key
echo "OPENAI_API_KEY=your_key_here" > .env
```

### Step 3: Run a Basic Game
```python
from game import AgenticPoker
from agents.agent import Agent
from datetime import datetime


# Create AI players with unique configurations
players = [
    Agent(name="Alice", chips=1000, strategy_style="Aggressive Bluffer"),
    Agent(name="Bob", chips=1000, strategy_style="Calculated and Cautious"),
    Agent(name="Charlie", chips=1000, strategy_style="Chaotic and Unpredictable"),
]


# Start a poker game with custom settings
game = AgenticPoker(
    players,
    starting_chips=1000,
    small_blind=10,
    big_blind=20,
    session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
)
game.start_game()
```

---

## Customization Options

### Strategy Styles
Define unique AI playing strategies:
- **Aggressive Bluffer**: High aggression, frequent bluffs, psychological pressure
- **Calculated and Cautious**: Tight play, selective aggression, mathematical precision
- **Chaotic and Unpredictable**: Erratic moves, table talk, emotional decisions

### AI Configuration
Customize AI behavior for any personality:
```python
player = Agent(
    name="Alice",
    chips=1000,
    strategy_style="Aggressive Bluffer",
    communication_style="Intimidating",
    use_reasoning=True,
    use_reflection=True,
    use_planning=True,
    use_opponent_modeling=True,
    use_reward_learning=True,
    learning_rate=0.1,
    personality_traits={
        "aggression": 0.5,
        "bluff_frequency": 0.5,
        "risk_tolerance": 0.5
    }
)
```

### Game Parameters
Adjust game rules to suit your preferences:
```python
game = AgenticPoker(
    players=players,
    starting_chips=1500,
    small_blind=15,
    big_blind=30,
    ante=5,
    max_rounds=50,
    tournament_mode=True,
)
```

---

## Testing & Logging

### Testing
Run the full test suite:
```bash
pytest tests/ --cov=./ --cov-report=xml
```
Focus on specific modules:
```bash
pytest tests/game/       # Game logic
pytest tests/agents/     # AI behavior
pytest tests/data/      # Data management
```

### Logging
Detailed logs track every aspect of the game:
- Player actions and decisions
- Betting rounds and hand evaluations
- AI reasoning processes
- Memory operations and state validation
- Side pot calculations and chip tracking
Logs are saved in session-specific files under `logs/`.

---

## Documentation
Explore detailed guides for all components:
- [Quickstart Guide](docs/quickstart.md)
- [Benefits of AI Poker Research](docs/benefits.md)
- [Example Log](docs/example_game.log)
- [AI Agent Configuration](docs/llm_agent.md)
- [Game Logic](docs/game/)
- [Strategy Planner](docs/strategy_planner.md)
