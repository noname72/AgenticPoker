from typing import List, Optional, Tuple, Union
from .player import Player
from .types import SidePot
import logging


def betting_round(
    players: List[Player], current_pot: int, game_state: Optional[dict] = None
) -> Union[int, Tuple[int, List[SidePot]]]:
    """
    Execute a betting round among active players.

    Args:
        players: List of players in the betting round
        current_pot: Current amount in the pot
        game_state: Optional dictionary containing current game state for AI decisions

    Returns:
        Either:
        - int: New pot amount (when no side pots)
        - Tuple[int, List[SidePot]]: New pot amount and list of side pots
    """
    logging.debug(f"Starting betting round with pot: ${current_pot}")
    logging.debug(f"Active players: {[p.name for p in active_players]}")

    active_players = [p for p in players if not p.folded]
    if not active_players:
        return current_pot

    # Track bets and all-in players
    all_in_players = []
    current_bet = 0
    pot = current_pot
    max_bet = 0  # Track highest bet for side pot calculations

    # Each player gets a chance to bet
    for player in active_players:
        if player.chips == 0:  # Skip players who are already all-in
            continue

        # Get player's action
        if hasattr(player, "decide_action"):
            decision = player.decide_action(game_state)
            action, amount = decision if isinstance(decision, tuple) else (decision, current_bet)
        else:
            action, amount = "call", current_bet

        # Handle the action
        if action == "fold":
            player.folded = True
        elif action in ("call", "raise"):
            # Calculate maximum possible bet
            max_possible_bet = min(amount, player.chips)
            actual_bet = player.place_bet(max_possible_bet)
            pot += actual_bet
            max_bet = max(max_bet, actual_bet + player.bet)

            if player.chips == 0:  # Player went all-in
                all_in_players.append(player)
                # Immediately calculate side pots when someone goes all-in
                side_pots = calculate_side_pots(
                    [p for p in active_players if not p.folded],
                    all_in_players
                )
                return pot, side_pots

            if action == "raise":
                current_bet = max_possible_bet

    # If there were any all-in players, return side pots
    if all_in_players:
        side_pots = calculate_side_pots(
            [p for p in active_players if not p.folded],
            all_in_players
        )
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
            logging.debug(f"  Pot {i+1}: ${pot.amount} - Eligible: {[p.name for p in pot.eligible_players]}")

    return side_pots
