import logging

from poker_game import PokerGame

# Modified logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            "poker_game.log", mode="w"
        ),  # 'w' mode overwrites the file each run
        logging.StreamHandler(),  # This maintains console output
    ],
)

if __name__ == "__main__":
    game = PokerGame()
    game.play_round()
