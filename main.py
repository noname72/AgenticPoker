from game import PokerGame
from game.ai_player import AIPlayer
from util import setup_logging
from datetime import datetime

# Generate unique session ID
session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

# Set up logging with session ID
setup_logging(0)

# Create AI players with different strategies
players = [
    AIPlayer("Alice", chips=1000, strategy_style="Aggressive Bluffer"),
    AIPlayer("Bob", chips=1000, strategy_style="Calculated and Cautious"),
    AIPlayer("Charlie", chips=1000, strategy_style="Chaotic and Unpredictable"),
    AIPlayer("Dana", chips=1000, strategy_style="Aggressive Bluffer"),
]

# Create game with session ID
game = PokerGame(
    players,
    starting_chips=1000,
    small_blind=50,
    big_blind=100,
    ante=10,
    session_id=0
)

game.start_game()
