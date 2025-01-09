import logging
from datetime import datetime

from agents.agent import Agent
from agents.random_agent import RandomAgent
from game.tournament import PokerTournament
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

# Load existing agent configurations
agent_configs = load_agent_configs()

# Create a larger pool of players for the tournament
players = [
    Agent(
        "Alice",
        chips=5000,  # Higher starting chips for tournament
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
        chips=5000,
        strategy_style="Calculated and Cautious",
        use_reasoning=True,
        use_reflection=False,
        use_planning=True,
        use_opponent_modeling=True,
        config=agent_configs.get("Bob"),
        session_id=session_id,
        communication_style="Analytical",
    ),
    Agent(
        "Charlie",
        chips=5000,
        strategy_style="Chaotic and Unpredictable",
        use_reasoning=True,
        use_reflection=False,
        use_planning=False,
        use_opponent_modeling=True,
        config=agent_configs.get("Charlie"),
        session_id=session_id,
        communication_style="Friendly",
    ),
    RandomAgent("Randy", chips=5000),
    Agent(
        "David",
        chips=5000,
        strategy_style="Tight and Aggressive",
        use_reasoning=True,
        use_planning=True,
        config=agent_configs.get("David", {}),
        session_id=session_id,
    ),
    Agent(
        "Eve",
        chips=5000,
        strategy_style="Loose and Passive",
        use_reasoning=True,
        config=agent_configs.get("Eve", {}),
        session_id=session_id,
    ),
]

# Tournament structure with increasing blinds
blind_schedule = [
    {"small_blind": 25, "big_blind": 50, "ante": 0},  # Level 1
    {"small_blind": 50, "big_blind": 100, "ante": 10},  # Level 2
    {"small_blind": 75, "big_blind": 150, "ante": 15},  # Level 3
    {"small_blind": 100, "big_blind": 200, "ante": 25},  # Level 4
    {"small_blind": 150, "big_blind": 300, "ante": 35},  # Level 5
    {"small_blind": 200, "big_blind": 400, "ante": 50},  # Level 6
    {"small_blind": 300, "big_blind": 600, "ante": 75},  # Level 7
    {"small_blind": 400, "big_blind": 800, "ante": 100},  # Level 8
    {"small_blind": 500, "big_blind": 1000, "ante": 125},  # Level 9
    {"small_blind": 750, "big_blind": 1500, "ante": 150},  # Level 10
]


def run_tournament():
    # Clear previous game data
    clear_results_directory()

    logger.info("\n" + "=" * 70)
    logger.info("New Poker Tournament Started")
    logger.info("=" * 70)
    logger.info(f"Number of players: {len(players)}")
    logger.info(f"Starting chips: 5000")
    logger.info(f"Blind levels: {len(blind_schedule)}")
    logger.info(f"Level duration: 15 minutes")
    logger.info("=" * 70 + "\n")

    # Create and start the tournament
    tournament = PokerTournament(
        players=players,
        buy_in=100,  # Buy-in amount (for tracking)
        starting_chips=1000,  # Starting stack
        blind_schedule=blind_schedule,
        level_duration_minutes=1,  # 15 minutes per level
    )

    # Run the tournament
    tournament.start_tournament()


if __name__ == "__main__":
    run_tournament()
