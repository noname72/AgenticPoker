import logging
from typing import List, Optional, Tuple, Union

from .player import Player
from .types import SidePot


def betting_round(
    players: List[Player], current_pot: int, game_state: Optional[dict] = None
) -> Union[int, Tuple[int, List[SidePot]]]:
    """Execute a betting round among active players."""
    active_players = [p for p in players if not p.folded]

    logging.debug(f"Starting betting round with pot: ${current_pot}")
    logging.debug(f"Active players: {[p.name for p in active_players]}")

    if not active_players:
        return current_pot

    # Track bets and all-in players
    all_in_players = []
    current_bet = 0
    pot = current_pot
    round_complete = False
    last_raiser = None

    # Reset player bets for this round
    for player in active_players:
        player.bet = 0

    # Set initial bet if provided in game state
    if game_state and "current_bet" in game_state:
        current_bet = game_state["current_bet"]

    # Set minimum bet to 10 if no current bet
    if current_bet == 0:
        current_bet = 10

    while not round_complete:
        round_complete = True  # Will be set to False if any player needs to act again
        players_acted = set()  # Track which players have acted this round

        for player in active_players:
            if player.folded or player.chips == 0:
                continue

            # Check if player needs to act
            needs_to_act = (
                player.bet < current_bet
                or player == last_raiser
                or current_bet == 0
                or player not in players_acted  # Ensure each player acts at least once
            )

            if not needs_to_act:
                continue

            # Get player's action
            if hasattr(player, "decide_action"):
                decision = player.decide_action(game_state)
                action, amount = (
                    decision if isinstance(decision, tuple) else (decision, current_bet)
                )
            else:
                # Default to calling current bet
                action, amount = "call", current_bet

            # Handle invalid actions by converting to call
            if action not in ("fold", "call", "raise"):
                action = "call"
                amount = current_bet

            # Handle the action
            if action == "fold":
                player.folded = True
                active_players = [p for p in active_players if not p.folded]

            elif action in ("call", "raise"):
                # Handle negative or invalid amounts
                amount = max(0, amount)

                # Calculate actual bet amount
                if action == "call":
                    to_call = current_bet - player.bet
                    bet_amount = min(to_call, player.chips)
                else:  # raise
                    # Ensure raise is at least the current bet
                    amount = max(amount, current_bet)
                    bet_amount = min(amount, player.chips)

                    # Only update current bet if it's a valid raise
                    if bet_amount > current_bet:
                        current_bet = bet_amount
                        last_raiser = player
                        round_complete = False  # Other players need to act
                    else:
                        # Convert to call if can't raise enough
                        action = "call"
                        bet_amount = min(current_bet - player.bet, player.chips)

                # Place the bet
                actual_bet = player.place_bet(bet_amount)
                pot += actual_bet

                # Check for all-in
                if player.chips == 0:
                    all_in_players.append(player)

            players_acted.add(player)

        # Check if betting is complete
        active_with_chips = [p for p in active_players if p.chips > 0]
        if len(active_with_chips) <= 1:
            round_complete = True
        elif all(p.bet == current_bet for p in active_players if not p.folded):
            round_complete = True

    # Calculate side pots if there were any all-ins
    if all_in_players:
        side_pots = calculate_side_pots(active_players, all_in_players)
        return pot, side_pots

    return pot


def calculate_side_pots(
    active_players: List[Player], all_in_players: List[Player]
) -> List[SidePot]:
    """Calculate side pots when players are all-in."""
    # Sort all-in players by their total bet amount
    all_in_players.sort(key=lambda p: p.bet)

    side_pots = []
    previous_bet = 0

    # Calculate main pot first (everyone can win this)
    min_bet = min(p.bet for p in active_players)
    if min_bet > 0:
        eligible = [p for p in active_players]
        side_pots.append(SidePot(min_bet * len(eligible), eligible))
        previous_bet = min_bet

    # Calculate additional side pots
    for all_in_player in all_in_players:
        bet_difference = all_in_player.bet - previous_bet
        if bet_difference > 0:
            # Find eligible players for this side pot
            eligible = [p for p in active_players if p.bet >= all_in_player.bet]
            pot_amount = bet_difference * len(eligible)
            if pot_amount > 0:
                side_pots.append(SidePot(pot_amount, eligible))
        previous_bet = all_in_player.bet

    # Calculate final side pot for players who bet more than all all-in players
    remaining_players = [p for p in active_players if p.chips > 0]
    if remaining_players:
        max_bet = max(p.bet for p in remaining_players)
        if max_bet > previous_bet:
            pot_amount = (max_bet - previous_bet) * len(remaining_players)
            side_pots.append(SidePot(pot_amount, remaining_players))

    if side_pots:
        logging.debug("Side pots created:")
        for i, pot in enumerate(side_pots):
            logging.debug(
                f"  Pot {i+1}: ${pot.amount} - Eligible: {[p.name for p in pot.eligible_players]}"
            )

    return side_pots


def log_action(
    player: Player, action: str, amount: int = 0, current_bet: int = 0, pot: int = 0
) -> None:
    """Log player actions with clear all-in indicators."""
    action_str = f"{player.name}'s turn:"
    if hasattr(player, "hand"):
        action_str += f"\n  Hand: {player.hand}"

    action_str += f"\n  Current bet to call: ${current_bet}"
    action_str += f"\n  Player chips: ${player.chips}"
    action_str += f"\n  Player current bet: ${player.bet}"
    action_str += f"\n  Current pot: ${pot}"

    if action == "fold":
        action_str += f"\n{player.name} folds"
    elif action == "call":
        all_in = amount >= player.chips
        status = " (all in)" if all_in else ""
        action_str += f"\n{player.name} calls ${amount}{status}"
    elif action == "raise":
        all_in = amount >= player.chips
        status = " (all in)" if all_in else ""
        action_str += f"\n{player.name} raises to ${amount}{status}"

    logging.info(action_str)
