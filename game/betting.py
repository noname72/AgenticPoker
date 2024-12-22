import logging
from typing import List

from game.player import Player


def betting_round(players: List["Player"], pot: int, start_index: int = 0) -> int:
    """
    Conducts a complete betting round in a poker game.

    Manages the flow of betting for a single round (pre-flop, flop, turn, or river),
    handling all player actions until the betting is complete or only one player remains.

    Args:
        players (List[Player]): List of all players in the game
        pot (int): Current pot amount before this betting round
        start_index (int, optional): Index of the first player to act. Defaults to 0.

    Returns:
        int: Final pot amount after all bets are placed

    Side Effects:
        - Updates player chip counts
        - Updates player bet amounts
        - May cause players to fold
        - Logs all betting actions and pot changes

    Note:
        The round ends when either:
        - Only one player remains (others folded)
        - All active players have either:
            a) Matched the current bet
            b) Gone all-in for a lesser amount
            c) Folded
    """
    logging.info(f"\n{'='*20} BETTING ROUND {'='*20}")
    logging.info(f"Starting pot: ${pot}")

    round_contributions = {p: 0 for p in players}
    current_bet = max(p.bet for p in players)

    logging.info("\nInitial state:")
    for player in players:
        if not player.folded:
            logging.info(f"  {player.name}: ${player.chips} chips, ${player.bet} bet")

    # Track individual contributions this round
    last_raiser = None
    index = start_index

    while True:
        player = players[index]

        # Skip folded players
        if player.folded:
            index = (index + 1) % len(players)
            continue

        # Stop if we've gone around the table with no new raises
        if player == last_raiser:
            break

        # If player has matched current bet and we've gone around once, we're done
        if player.bet == current_bet and last_raiser is not None:
            index = (index + 1) % len(players)
            continue

        logging.info(f"\n{player.name}'s turn:")
        logging.info(f"  Hand: {player.hand.show()}")
        logging.info(f"  Current bet: ${current_bet}")
        logging.info(f"  Player chips: ${player.chips}")
        logging.info(f"  Player current bet: ${player.bet}")

        action = decide_action(player, current_bet, last_raiser is not None)

        if action == "fold":
            player.fold()
            log_action(player, "fold", current_bet=current_bet, pot=pot)
        elif action == "call":
            call_amount = min(current_bet - player.bet, player.chips)
            if call_amount > 0:
                actual_bet = player.place_bet(call_amount)
                round_contributions[player] += actual_bet
                pot += actual_bet
                log_action(
                    player, "call", amount=actual_bet, current_bet=current_bet, pot=pot
                )
        elif action.startswith("raise"):
            _, raise_amount = action.split()
            raise_amount = min(int(raise_amount), player.chips)
            total_bet = min(current_bet - player.bet + raise_amount, player.chips)

            if total_bet > 0:
                actual_bet = player.place_bet(total_bet)
                round_contributions[player] += actual_bet
                pot += actual_bet
                current_bet = player.bet
                last_raiser = player
                log_action(
                    player, "raise", amount=actual_bet, current_bet=current_bet, pot=pot
                )
        else:  # check
            if current_bet > player.bet:
                player.fold()
                log_action(player, "fold", current_bet=current_bet, pot=pot)
            else:
                log_action(player, "check", current_bet=current_bet, pot=pot)

        # Add detailed pot tracking after each action
        logging.info(f"\nCurrent pot: ${pot}")
        logging.info("Round contributions:")
        for p, amount in round_contributions.items():
            if amount > 0:
                logging.info(f"  {p.name}: ${amount}")

        # Check if only one player remains
        active_players = [p for p in players if not p.folded]
        if len(active_players) == 1:
            break

        index = (index + 1) % len(players)

    logging.info("\nBetting round complete:")
    logging.info(f"Final pot: ${pot}")
    logging.info("Player contributions this round:")
    for player, amount in round_contributions.items():
        if amount > 0:
            logging.info(f"  {player.name}: ${amount}")
    logging.info(f"{'='*50}\n")
    return pot


def decide_action(player: "Player", current_bet: int, raised: bool) -> str:
    """
    Determines the AI player's next action in the betting round.

    Implements the decision-making logic for AI players, considering their
    current chips, the bet they need to call, and whether there's been a raise.

    Args:
        player (Player): The player whose turn it is
        current_bet (int): The current bet amount that needs to be matched
        raised (bool): Whether the bet has been raised in this round

    Returns:
        str: Action to take, one of:
            - "check": Stay in without betting (only valid when current_bet == player.bet)
            - "fold": Give up the hand
            - "call": Match the current bet
            - "raise {amount}": Increase the bet by {amount}

    Side Effects:
        - Logs decision-making process and relevant state

    Note:
        Currently implements a simple random strategy for demonstration purposes.
        Future versions should implement more sophisticated betting strategies
        based on:
        - Hand strength
        - Position
        - Pot odds
        - Player tendencies
        - Stack sizes
    """
    import random

    logging.debug(f"Deciding action for {player.name}:")
    logging.debug(f"  Current bet: ${current_bet}")
    logging.debug(f"  Already raised: {raised}")
    logging.debug(f"  Player chips: ${player.chips}")

    if current_bet == 0:
        return (
            "check" if random.random() < 0.7 else f"raise {random.choice([10, 20, 30])}"
        )
    else:
        return random.choice(["fold", "call", f"raise {random.choice([10, 20])}"])


def log_action(
    player: "Player", action: str, amount: int = 0, current_bet: int = 0, pot: int = 0
) -> None:
    """
    Helper to log player actions consistently.

    Args:
        player: The player taking the action
        action: The type of action ("fold", "call", "raise", or "check")
        amount: The amount bet/called/raised (if applicable)
        current_bet: The current bet amount to call
        pot: The current pot size
    """
    action_str = {
        "fold": "folds",
        "call": f"calls ${amount}",
        "raise": f"raises to ${amount}",
        "check": "checks",
    }[action]

    logging.info(f"\n{player.name} {action_str}")
    logging.info(f"  Chips remaining: ${player.chips}")
    logging.info(f"  Current pot: ${pot}")
    if current_bet > 0:
        logging.info(f"  Current bet to call: ${current_bet}")
