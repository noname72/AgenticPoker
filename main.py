import logging
from datetime import datetime

from agents.agent import Agent
from agents.random_agent import RandomAgent
from game import AgenticPoker, GameConfig
from loggers.config import configure_loggers
from util import (
    clear_results_directory,
    ensure_directory_structure,
    load_agent_configs,
    setup_logging,
)

# Remove the basicConfig call since setup_logging will handle it
logger = logging.getLogger(__name__)

# Ensure required directories exist
ensure_directory_structure()

# Generate unique session ID
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# Set up logging with session ID
setup_logging(session_id)

# Configure specific logger levels
configure_loggers(
    {
        "betting": logging.INFO,
        "llm": logging.INFO,  # Set to DEBUG to see prompts/responses
        "table": logging.INFO,
    }
)

# Load existing agent configurations or create new ones
agent_configs = load_agent_configs()

# Create AI players with different strategies and features
players = [
    Agent(
        "Alice",
        chips=1000,
        strategy_style="Aggressive Bluffer",
        use_reasoning=True,
        use_reflection=True,
        use_planning=True,
        use_opponent_modeling=True,
        use_reward_learning=True,
        learning_rate=0.1,
        config=agent_configs.get("Alice"),
        session_id=session_id,
        communication_style="Intimidating",
    ),
    Agent(
        "Bob",
        chips=1000,
        strategy_style="Calculated and Cautious",
        use_reasoning=True,
        use_reflection=False,
        use_planning=False,
        use_opponent_modeling=True,
        config=agent_configs.get("Bob"),
        session_id=session_id,
        communication_style="Analytical",
    ),
    Agent(
        "Charlie",
        chips=1000,
        strategy_style="Chaotic and Unpredictable",
        use_reasoning=False,
        use_reflection=False,
        use_planning=False,
        use_opponent_modeling=False,
        config=agent_configs.get("Charlie"),
        session_id=session_id,
        communication_style="Friendly",
    ),
    RandomAgent(
        "Randy",
        chips=1000,
    ),
]

# Create game with session ID
game = AgenticPoker(
    players,
    config=GameConfig(
        starting_chips=1000,  #! is this a needed parameter if we have chips in agent?
        small_blind=50,
        big_blind=100,
        ante=10,
        session_id=session_id,
        max_raise_multiplier=3,  # Maximum raise can be 3x the current bet
        max_raises_per_round=4,  # Limit number of raises per betting round
        min_bet=100,  # Add this line to enforce minimum bet equal to big blind
    ),
)


def main():
    # Clear previous game data BEFORE creating agents
    clear_results_directory()

    logger.info("\n" + "=" * 70)
    logger.info("New Poker Game Session Started")
    logger.info("=" * 70 + "\n")

    game.play_game()


if __name__ == "__main__":
    main()
