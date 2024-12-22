import logging
from typing import List

from game.player import Player


def betting_round(players: List["Player"], pot: int, start_index: int = 0) -> int:
    """
    Conducts a complete betting round in a poker game.

    Args:
        players: List of Player objects participating in the game
        pot: Current size of the pot in dollars
        start_index: Index of the player who starts the betting round (default: 0)

    Returns:
        int: Updated pot size after the betting round completes

    Note:
        The round continues until either:
        - Only one player remains (others folded)
        - All active players have matched the current bet or are all-in
    """
    logging.info(f"\n{'='*20} BETTING ROUND {'='*20}")
    logging.info(f"Starting pot: ${pot}")

    round_contributions = {p: 0 for p in players}
    current_bet = max(p.bet for p in players)
    last_raiser = None
    index = start_index
    betting_complete = False

    logging.info("\nInitial state:")
    for player in players:
        if not player.folded:
            logging.info(f"  {player.name}: ${player.chips} chips, ${player.bet} bet")

    while not betting_complete:
        active_players = [p for p in players if not p.folded]

        # End conditions
        if len(active_players) <= 1:
            betting_complete = True
            break

        # Check if all active players have matched the current bet or are all-in
        all_matched = all(
            (p.bet == current_bet or p.chips == 0) for p in active_players
        )
        if all_matched and (last_raiser is None or index == last_raiser):
            betting_complete = True
            break

        player = players[index]

        # Skip folded players or those who are all-in and have matched
        if player.folded or (player.chips == 0 and player.bet >= current_bet):
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
                last_raiser = index
                log_action(
                    player, "raise", amount=actual_bet, current_bet=current_bet, pot=pot
                )

        logging.info(f"\nCurrent pot: ${pot}")
        logging.info("Round contributions:")
        for p, amount in round_contributions.items():
            if amount > 0:
                logging.info(f"  {p.name}: ${amount}")

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
    Determines the player's next action in the betting round.

    Args:
        player: Player object whose action is being determined
        current_bet: The current bet amount that needs to be matched
        raised: Boolean indicating if there has been a raise in this round

    Returns:
        str: Action string in one of these formats:
            - "fold"
            - "call"
            - "raise {amount}"

    Note:
        For AI players, uses their decide_action() method with enhanced game state
        For non-AI players, uses a random strategy as fallback
    """
    # If player is all-in, they can only check/call
    if player.chips == 0:
        return "call"

    # If player has less than big blind, they should just call
    if player.chips < current_bet * 2:
        return "call"

    if hasattr(player, "decide_action"):  # Check if it's an AI player
        # Create a richer game state description for AI
        game_state = (
            f"Current bet: ${current_bet}, "
            f"Your chips: ${player.chips}, "
            f"Your bet: ${player.bet}, "
            f"Hand: {player.hand.show()}, "
            f"Position: {'dealer' if raised else 'non-dealer'}, "
            f"Pot odds: {current_bet/(current_bet + player.chips):.2f}"
        )
        action = player.decide_action(game_state)

        # Normalize AI action to match expected format
        if action == "raise":
            # AI players make reasonable raise amounts based on pot and stack
            raise_amount = min(max(current_bet * 2, 20), player.chips)
            return f"raise {raise_amount}"
        return action
    else:
        # Fallback to original random strategy for non-AI players
        import random

        if current_bet == 0:
            return (
                "check"
                if random.random() < 0.7
                else f"raise {random.choice([10, 20, 30])}"
            )
        else:
            return random.choice(["fold", "call", f"raise {random.choice([10, 20])}"])


def log_action(
    player: "Player", action: str, amount: int = 0, current_bet: int = 0, pot: int = 0
) -> None:
    """
    Logs player actions in a consistent format to the game log.

    Args:
        player: The player taking the action
        action: Action type ("fold", "call", "raise", or "check")
        amount: Amount bet/called/raised (default: 0)
        current_bet: Current bet amount to call (default: 0)
        pot: Current pot size (default: 0)

    Note:
        Formats and logs:
        - The action taken
        - Remaining chips
        - Current pot size
        - Current bet to call (if applicable)
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


def handle_betting_round(self, players, current_bet=0, min_raise=None):
    """
    Handles a complete round of betting among active players.

    Args:
        players: List of players in the game
        current_bet: Starting bet amount for the round (default: 0)
        min_raise: Minimum raise amount (default: None)

    Returns:
        int: Total amount bet during the round

    Note:
        Continues until all active players have:
        - Acted at least once
        - Either folded, matched the highest bet, or gone all-in
        Tracks player actions and updates bets accordingly
    """
    # Initialize betting round
    active_players = [p for p in players if not p.folded]
    if not active_players:
        return 0

    # Track who has acted and had chance to match highest bet
    players_acted = set()
    highest_bet = current_bet

    # Continue until all active players have acted and matched highest bet
    while len(players_acted) < len(active_players) or any(
        p.current_bet != highest_bet for p in active_players if not p.folded
    ):

        for player in active_players:
            if player.folded:
                continue

            # Skip if player is all-in
            if player.chips == 0:
                players_acted.add(player)
                continue

            # Skip if player has acted and matched highest bet
            if player in players_acted and player.current_bet == highest_bet:
                continue

            action = player.get_action(highest_bet)

            if action.type == "fold":
                player.folded = True
                players_acted.add(player)

            elif action.type in ("call", "check"):
                call_amount = highest_bet - player.current_bet
                if call_amount > 0:
                    player.bet(call_amount)
                players_acted.add(player)

            elif action.type == "raise":
                raise_amount = action.amount
                player.bet(raise_amount)
                highest_bet = player.current_bet
                # Clear players_acted except for folders and all-ins
                players_acted = {p for p in players_acted if p.folded or p.chips == 0}
                players_acted.add(player)

    return sum(p.current_bet for p in players)
