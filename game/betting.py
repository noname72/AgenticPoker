from typing import List, Optional, Tuple, Union
from .player import Player
from .types import SidePot


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
    active_players = [p for p in players if not p.folded]
    if not active_players:
        return current_pot

    # Track bets and all-in players
    all_in_players = []
    current_bet = 0
    pot = current_pot

    # Each player gets a chance to bet
    for player in active_players:
        if player.chips == 0:  # Skip players who are already all-in
            continue

        # Get player's action
        if hasattr(player, "decide_action"):
            # Handle LLMAgent's decision format
            decision = player.decide_action(game_state)
            if isinstance(decision, tuple):
                action, amount = decision
            else:
                # LLMAgent might return just the action
                action = decision
                amount = current_bet if action == "call" else player.chips
        else:
            action, amount = "call", current_bet

        # Handle the action
        if action == "fold":
            player.folded = True
        elif action in ("call", "raise"):
            bet_amount = min(amount, player.chips)  # Can't bet more than you have
            actual_bet = player.place_bet(bet_amount)
            pot += actual_bet

            if player.chips == 0:  # Player went all-in
                all_in_players.append(player)

            if action == "raise":
                current_bet = amount

    # If there were any all-in players, calculate side pots
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

    for all_in_player in all_in_players:
        bet_difference = all_in_player.bet - previous_bet
        if bet_difference > 0:
            # Find eligible players for this side pot
            eligible = [p for p in active_players if p.bet >= all_in_player.bet]
            pot_amount = bet_difference * len(eligible)
            side_pots.append(SidePot(pot_amount, eligible))
        previous_bet = all_in_player.bet

    return side_pots
