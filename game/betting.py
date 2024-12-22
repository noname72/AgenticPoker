from typing import List

from game.player import Player


def betting_round(players: List["Player"], pot: int, start_index: int = 0) -> int:
    """
    Conducts a betting round in a poker game.

    Args:
        players (List[Player]): List of players in the game
        pot (int): Current pot amount
        start_index (int, optional): Index of the player to start the betting. Defaults to 0.

    Returns:
        int: Updated pot amount after the betting round

    Note:
        The betting continues until all active players have either:
        - Matched the current bet
        - Folded their hand
        Players who have already folded are skipped but counted towards the total.
    """
    current_bet = 0
    raised = False
    num_players = len(players)
    players_acted = 0
    index = start_index

    while players_acted < num_players:
        player = players[index]

        if player.folded:
            players_acted += 1
            index = (index + 1) % num_players
            continue

        if player.bet == current_bet and not raised:
            players_acted += 1
            index = (index + 1) % num_players
            continue

        action = decide_action(player, current_bet, raised)

        if action == "fold":
            player.fold()
            print(f"{player.name} folds.")
        elif action == "call":
            call_amount = current_bet - player.bet
            player.place_bet(call_amount)
            pot += call_amount
            print(f"{player.name} calls.")
        elif action.startswith("raise"):
            _, raise_amount = action.split()
            raise_amount = int(raise_amount)
            total_needed = (current_bet - player.bet) + raise_amount
            player.place_bet(total_needed)
            pot += total_needed
            current_bet += raise_amount
            raised = True
            print(f"{player.name} raises to {current_bet}.")
        else:
            print(f"{player.name} checks.")

        players_acted += 1
        index = (index + 1) % num_players

    return pot


def decide_action(player: "Player", current_bet: int, raised: bool) -> str:
    """
    Determines the AI player's next action in the betting round.

    Args:
        player (Player): The player whose turn it is
        current_bet (int): The current bet amount that needs to be matched
        raised (bool): Whether the bet has been raised in this round

    Returns:
        str: Action to take, one of:
            - "check": Stay in without betting
            - "fold": Give up the hand
            - "call": Match the current bet
            - "raise {amount}": Increase the bet by {amount}

    Note:
        Currently implements a simple random strategy for demonstration purposes.
    """
    import random

    if current_bet == 0:
        return (
            "check" if random.random() < 0.7 else f"raise {random.choice([10, 20, 30])}"
        )
    else:
        return random.choice(["fold", "call", f"raise {random.choice([10, 20])}"])
