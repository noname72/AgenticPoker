import logging
from typing import Dict, List, Optional, Tuple

from .player import Player
from .types import SidePot
from . import betting
from .pot_manager import PotManager

def handle_post_draw_betting(
    players: List[Player],
    pot: int,
    game_state: dict,
    pot_manager: 'PotManager'
) -> Tuple[int, Optional[List[SidePot]]]:
    """
    Handle the post-draw betting round.

    Args:
        players: List of active players
        pot: Current pot amount
        game_state: Current game state dictionary
        pot_manager: PotManager instance handling pot calculations

    Returns:
        Tuple containing:
        - Updated pot amount
        - List of side pots (if any) or None
    """
    result = betting.betting_round(players, pot, game_state)
    
    # Handle both return types
    if isinstance(result, tuple):
        new_pot, side_pots = result
    else:
        new_pot = result
        side_pots = None
    
    return new_pot, side_pots

def handle_showdown(
    players: List[Player],
    pot: int,
    initial_chips: Dict[Player, int]
) -> None:
    """
    Handle the showdown phase where winners are determined and pots are distributed.

    Args:
        players: List of active players
        pot: Final pot amount
        initial_chips: Dictionary of starting chip counts for each player

    Side Effects:
        - Updates player chip counts
        - Logs showdown results and chip movements
    """
    active_players = [p for p in players if not p.folded]

    # Log showdown hands
    logging.info("\n=== Showdown ===")
    for player in active_players:
        logging.info(f"{player.name}'s hand: {player.hand.show()}")

    if len(active_players) == 1:
        # Single player remaining gets the pot
        winner = active_players[0]
        winner.chips += pot
        logging.info(f"{winner.name} wins ${pot} (all others folded)")
    else:
        # Multiple players - evaluate hands
        winners = _evaluate_hands(active_players)
        if winners:
            split_amount = pot // len(winners)
            remainder = pot % len(winners)  # Handle odd chips
            for i, winner in enumerate(winners):
                # Add one chip to early winners if there's a remainder
                extra = 1 if i < remainder else 0
                winner.chips += split_amount + extra
                logging.info(f"{winner.name} wins ${split_amount + extra}")

    _log_chip_movements(players, initial_chips)

def _evaluate_hands(players: List[Player]) -> List[Player]:
    """
    Evaluate player hands to determine winner(s).

    Args:
        players: List of players to evaluate

    Returns:
        List[Player]: List of winning players (multiple in case of tie)
    """
    if not players:
        return []

    # Find best hand(s)
    best_players = [players[0]]
    best_hand = players[0].hand

    for player in players[1:]:
        try:
            comparison = player.hand.compare_to(best_hand)
        except AttributeError:
            # For test mocks, use direct comparison
            if player.hand > best_hand:
                comparison = 1
            elif player.hand == best_hand:
                comparison = 0
            else:
                comparison = -1

        if comparison > 0:  # Current player has better hand
            best_players = [player]
            best_hand = player.hand
        elif comparison == 0:  # Tie
            best_players.append(player)

    return best_players

def _log_chip_movements(players: List[Player], initial_chips: Dict[Player, int]) -> None:
    """Log the chip movements for each player from their initial amounts."""
    for player in players:
        if player.chips != initial_chips[player]:
            net_change = player.chips - initial_chips[player]
            logging.info(
                f"{player.name}: ${initial_chips[player]} → ${player.chips} ({net_change:+d})"
            ) 