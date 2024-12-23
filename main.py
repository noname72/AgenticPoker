import logging
from datetime import datetime

from agents.llm_agent import LLMAgent
from game import PokerGame
from util import (
    clear_results_directory,
    ensure_directory_structure,
    load_agent_configs,
    setup_logging,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure required directories exist
ensure_directory_structure()

# Generate unique session ID
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# Set up logging with session ID
setup_logging(session_id)

# Load existing agent configurations or create new ones
agent_configs = load_agent_configs()

# Create AI players with different strategies and features
players = [
    LLMAgent(
        "Alice",
        chips=1000,
        strategy_style="Aggressive Bluffer",
        use_reasoning=True,
        use_reflection=True,
        use_planning=True,
        use_opponent_modeling=True,
        config=agent_configs.get("Alice"),
    ),
    LLMAgent(
        "Bob",
        chips=1000,
        strategy_style="Calculated and Cautious",
        use_reasoning=True,
        use_reflection=False,
        use_planning=False,
        use_opponent_modeling=True,
        config=agent_configs.get("Bob"),
    ),
    LLMAgent(
        "Charlie",
        chips=1000,
        strategy_style="Chaotic and Unpredictable",
        use_reasoning=False,
        use_reflection=False,
        use_planning=False,
        use_opponent_modeling=False,
        config=agent_configs.get("Charlie"),
    ),
]

# Create game with session ID
game = PokerGame(
    players,
    starting_chips=1000,
    small_blind=50,
    big_blind=100,
    ante=10,
    session_id=session_id,
)


def main():
    # Clear previous game data
    clear_results_directory()

    logger.info("\n" + "=" * 70)
    logger.info("New Poker Game Session Started")
    logger.info("=" * 70 + "\n")

    game.start_game()


if __name__ == "__main__":
    main()
