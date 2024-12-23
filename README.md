# AI Poker Game

A sophisticated poker game simulation featuring AI players powered by Large Language Models (LLMs). The system implements 5-card draw poker with intelligent agents that can reason about their decisions, learn from past hands, and engage in natural language table talk.

## Features

### Core Game
- Complete 5-card draw poker implementation
- Robust hand evaluation and comparison
- Side pot handling for all-in situations
- Configurable game parameters (blinds, antes, etc.)
- Session-based gameplay with unique IDs
- Support for tournament and cash game formats

### AI Players
- LLM-powered decision making with:
  - Dynamic strategy adaptation
  - Probabilistic reasoning
  - Pattern recognition
  - Psychological modeling
- Multiple personality profiles:
  - Unique playing styles
  - Natural language communication
  - Contextual table talk
  - Emotional responses
- Advanced capabilities:
  - Strategic reasoning with explicit logic chains
  - Hand history reflection and learning
  - Multi-round planning and adaptation
  - Opponent modeling and exploitation
  - Bankroll management
  - Risk assessment

### Data Management
- SQLAlchemy ORM for game state persistence
- Comprehensive player statistics tracking
- Game replay and analysis tools
- Detailed action and event logging
- Performance analytics
- Machine learning integration ready

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your_key_here" > .env
```

3. Run a basic game:
```python
from game import PokerGame
from agents.llm_agent import LLMAgent

# Create AI players with different personalities
players = [
    LLMAgent(
        name="Alice",
        chips=1000,
        strategy_style="Aggressive Bluffer",
        use_reasoning=True,
        use_reflection=True
    ),
    LLMAgent(
        name="Bob",
        chips=1000,
        strategy_style="Calculated and Cautious",
        use_opponent_modeling=True
    ),
    LLMAgent(
        name="Charlie",
        chips=1000,
        strategy_style="Chaotic and Unpredictable"
    )
]

# Start the game with custom settings
game = PokerGame(
    players,
    starting_chips=1000,
    small_blind=10,
    big_blind=20,
    session_id=datetime.now().strftime("%Y%m%d_%H%M%S")
)
game.start_game()
```

## Project Structure

```
poker-ai/
├── agents/             # AI player implementations
│   ├── llm_agent.py   # LLM-based AI player
│   └── base_agent.py  # Base agent interface
├── game/              # Core poker game logic
│   ├── betting.py     # Betting round mechanics
│   ├── card.py        # Card representation
│   ├── deck.py        # Deck management
│   ├── evaluator.py   # Hand evaluation
│   ├── game.py        # Main game controller
│   ├── hand.py        # Hand representation
│   └── player.py      # Player state management
├── data/              # Data persistence
│   ├── model.py       # Database models
│   └── repositories.py # Data access layer
├── docs/              # Documentation
│   ├── game/          # Game module docs
│   └── data/          # Data layer docs
├── tests/             # Test suite
├── configs/           # Configuration files
└── main.py           # Application entry point
```

## Configuration

### Strategy Styles
- "Aggressive Bluffer" - High aggression, frequent bluffs, psychological warfare
- "Calculated and Cautious" - Mathematical approach, tight play, selective aggression
- "Chaotic and Unpredictable" - Mixed strategies, table talk, emotional decisions
- "Tight and Aggressive" - Premium hands only, maximum value extraction
- "Loose and Passive" - Speculative play, minimal aggression, trap setting

### Game Parameters
```python
game = PokerGame(
    players,
    starting_chips=1000,  # Starting stack for each player
    small_blind=10,       # Small blind amount
    big_blind=20,         # Big blind amount
    ante=5,               # Optional ante amount
    max_rounds=100,       # Optional maximum rounds
    session_id=None,      # Optional custom session ID
    tournament_mode=False # Tournament vs cash game
)
```

### AI Player Configuration
```python
player = LLMAgent(
    name="Alice",
    chips=1000,
    strategy_style="Aggressive Bluffer",
    use_reasoning=True,     # Enable detailed decision reasoning
    use_reflection=True,    # Enable learning from past hands
    use_planning=True,      # Enable multi-step planning
    use_opponent_modeling=True,  # Enable opponent behavior analysis
    personality_traits={    # Custom personality configuration
        "aggression": 0.8,
        "bluff_frequency": 0.7,
        "risk_tolerance": 0.6
    }
)
```

## Database Integration

```python
from data.model import Base
from data.repositories import GameRepository, PlayerRepository
from sqlalchemy import create_engine

# Set up database
engine = create_engine('sqlite:///poker_game.db')
Base.metadata.create_all(engine)

# Initialize repositories
game_repo = GameRepository(session)
player_repo = PlayerRepository(session)

# Create and track game
game_record = game_repo.create(
    small_blind=10,
    big_blind=20,
    ante=5,
    max_players=6
)

# Track player statistics
player_repo.update_stats(
    player_id=1,
    game_stats={
        "won": True,
        "winnings": 500,
        "pot_size": 1000,
        "duration": 300,
        "hands_played": 15,
        "showdowns_won": 3
    }
)
```

## Testing

Run the test suite:
```bash
# Run all tests
pytest tests/

# Generate coverage report
pytest tests/ --cov=./ --cov-report=xml

# Run specific test categories
pytest tests/game/       # Test game logic
pytest tests/agents/     # Test AI behavior
pytest tests/data/      # Test data layer
```

## Logging

The system provides comprehensive logging:
- Game configuration and setup
- Player actions and decisions
- Betting rounds and pot management
- Hand evaluations and showdowns
- Player eliminations and game outcomes
- AI reasoning and decision factors
- Performance metrics and statistics

Logs are written to both console and session-specific log files in the `logs/` directory.

## Documentation

- [Quickstart Guide](docs/quickstart.md)
- [Game Module Documentation](docs/game/)
- [AI Agent Documentation](docs/llm_agent.md)
- [Database Schema](docs/data/model.md)
- [Repository Pattern](docs/data/repositories.md)
- [Analysis Tools](docs/analysis.md)
- [Tournament Mode](docs/tournament.md)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for the GPT models powering the AI players
- The poker community for strategy insights
- Contributors and testers
