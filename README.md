# AgenticPoker

AgenticPoker is a poker game simulation featuring AI players powered by Large Language Models (LLMs). The system simulates **5-card draw poker**, with intelligent agents capable of making strategic decisions, learning from past hands, and engaging in natural language table talk. 

Designed for realism and adaptability, AgenticPoker offers a comprehensive poker experience, blending advanced AI capabilities with detailed game mechanics.

---

## Key Features

### Core Game Mechanics
- **Game Variants**: Fully implements 5-card draw poker.
- **Hand Evaluation**: Accurate hand evaluation and comparison logic.
- **Side Pot Management**: Handles complex all-in scenarios seamlessly.
- **Customizable Parameters**: Configure blinds, antes, starting chips, and game modes.
- **Session Tracking**: Unique session IDs for organized gameplay.
- **Formats**: Supports both tournament and cash game styles.

### AI Players
AgenticPoker introduces intelligent LLM-powered agents with unique personalities and advanced decision-making capabilities.

#### Decision-Making Capabilities:
- **Dynamic Strategy Adaptation**: Real-time adjustments based on gameplay.
- **Probabilistic Reasoning**: Calculates odds and expected value.
- **Pattern Recognition**: Identifies trends in opponent behavior.
- **Psychological Modeling**: Explores emotional and strategic manipulation.

#### Personality Profiles:
Each agent embodies a distinct playing style and communication approach:
- **Playing Styles**: Aggressive, cautious, unpredictable, or balanced strategies.
- **Communication Styles**: 
  - **Intimidating**: Applies psychological pressure.
  - **Analytical**: Focuses on probabilities and logical observations.
  - **Friendly**: Engages with light, strategic banter.
- **Emotional Traits**: Adaptive emotional responses, strategic banter, and table talk.

#### Advanced AI Features:
- Strategic reasoning with detailed logic chains.
- Hand history reflection for continuous learning.
- Multi-round planning and opponent modeling.
- Risk assessment and bankroll management.

---

## Data Management
AgenticPoker leverages robust data management tools for seamless game state tracking and analysis.

- **SQLAlchemy ORM**: For game state persistence.
- **Player Statistics**: Tracks wins, losses, earnings, and key performance metrics.
- **Replay & Analysis Tools**: Revisit and analyze past games.
- **Event Logging**: Detailed logs for all player actions and outcomes.
- **Machine Learning Integration**: Ready for advanced analytics and training.

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
from game import PokerGame
from agents.llm_agent import LLMAgent
from datetime import datetime

# Create AI players with unique configurations
players = [
    LLMAgent(name="Alice", chips=1000, strategy_style="Aggressive Bluffer"),
    LLMAgent(name="Bob", chips=1000, strategy_style="Calculated and Cautious"),
    LLMAgent(name="Charlie", chips=1000, strategy_style="Chaotic and Unpredictable"),
]

# Start a poker game with custom settings
game = PokerGame(
    players,
    starting_chips=1000,
    small_blind=10,
    big_blind=20,
    session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
)
game.start_game()
```

---

## Project Structure

```plaintext
poker-ai/
├── agents/             # AI player implementations
│   ├── llm_agent.py    # LLM-based AI player
│   └── base_agent.py   # Base agent interface
├── game/               # Core poker game logic
│   ├── betting.py      # Betting mechanics
│   ├── card.py         # Card representation
│   ├── deck.py         # Deck management
│   ├── evaluator.py    # Hand evaluation logic
│   ├── game.py         # Main game controller
│   ├── hand.py         # Hand representation
│   └── player.py       # Player state management
├── data/               # Data persistence layer
│   ├── model.py        # Database models
│   └── repositories.py # Data access utilities
├── docs/               # Documentation
├── tests/              # Test suite
└── main.py             # Application entry point
```

---

## Customization Options

### Strategy Styles
Define unique AI playing strategies:
- **Aggressive Bluffer**: High aggression, frequent bluffs, psychological pressure.
- **Calculated and Cautious**: Tight play, selective aggression, mathematical precision.
- **Chaotic and Unpredictable**: Erratic moves, table talk, emotional decisions.
- **Tight and Aggressive**: Premium hands, value-maximizing aggression.
- **Loose and Passive**: Speculative play, trap setting.

### AI Configuration
Customize AI behavior for any personality:
```python
player = LLMAgent(
    name="Alice",
    chips=1000,
    strategy_style="Aggressive Bluffer",
    communication_style="Intimidating",
    use_reasoning=True,
    use_reflection=True,
    use_opponent_modeling=True,
    personality_traits={
        "aggression": 0.8,
        "bluff_frequency": 0.7,
        "risk_tolerance": 0.6
    }
)
```

### Game Parameters
Adjust game rules to suit your preferences:
```python
game = PokerGame(
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

## Database Integration
Set up a database for persistent storage:
```python
from data.model import Base
from sqlalchemy import create_engine
from data.repositories import GameRepository, PlayerRepository

# Configure SQLite database
engine = create_engine('sqlite:///poker_game.db')
Base.metadata.create_all(engine)

# Initialize repositories
game_repo = GameRepository(engine)
player_repo = PlayerRepository(engine)
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
pytest tests/data/        # Data management
```

### Logging
Detailed logs track every aspect of the game:
- Player actions, decisions, and outcomes.
- Betting rounds and hand evaluations.
- AI reasoning and learning processes.
Logs are saved in session-specific files under `logs/`.

---

## Documentation
Explore detailed guides for all components:
- [Quickstart Guide](docs/quickstart.md)
- [AI Agent Configuration](docs/llm_agent.md)
- [Game Logic](docs/game/)
- [Data Management](docs/data/model.md)
- [Tournament Mode](docs/tournament.md)
