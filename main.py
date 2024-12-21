from poker_game import PokerGame
from util import setup_logging

if __name__ == "__main__":
    setup_logging()
    game = PokerGame()
    game.play_round()
