from datetime import datetime

from agents.llm_agent import LLMAgent
from game import PokerGame
from util import setup_logging

# Generate unique session ID
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# Set up logging with session ID
setup_logging(0)

# Create AI players with different strategies
players = [
    LLMAgent(
        "Alice",
        chips=1000,
        strategy_style="Aggressive Bluffer",
        use_reasoning=True,
        use_reflection=True,
    ),
    LLMAgent(
        "Bob",
        chips=1000,
        strategy_style="Calculated and Cautious",
        use_reasoning=True,
        use_reflection=False,
    ),
    LLMAgent(
        "Charlie",
        chips=1000,
        strategy_style="Chaotic and Unpredictable",
        use_reasoning=False,
        use_reflection=False,
    ),
]

# Create game with session ID
game = PokerGame(
    players, starting_chips=1000, small_blind=50, big_blind=100, ante=10, session_id=0
)

game.start_game()
