# import json

# from poker_game import PokerGame
# from util import load_agent_configs, setup_logging

# if __name__ == "__main__":
#     setup_logging()
#     agent_configs = load_agent_configs()
#     game = PokerGame(agent_configs=agent_configs)
#     game.play_round()
#     # Save updated agent configurations after the game
#     with open("agent_configs.json", "w") as f:
#         json.dump(agent_configs, f, indent=4)


from game import PokerGame

player_names = ["Alice", "Bob", "Charlie", "Dana"]
game = PokerGame(player_names, starting_chips=100, small_blind=5, big_blind=10)
game.start_game()
