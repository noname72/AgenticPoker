import logging
from typing import List, Optional, Tuple

from .player import Player
from .types import SidePot
from . import betting
from .pot_manager import PotManager

def handle_pre_draw_betting(
    players: List[Player],
    pot: int,
    dealer_index: int,
    game_state: dict,
    pot_manager: PotManager
) -> Tuple[int, Optional[List[SidePot]], bool]:
    """
    Handle the pre-draw betting round.

    Args:
        players: List of active players
        pot: Current pot amount
        dealer_index: Position of dealer button
        game_state: Current game state dictionary
        pot_manager: PotManager instance for handling pot updates

    Returns:
        Tuple containing:
        - new pot amount (int)
        - list of side pots if any (Optional[List[SidePot]])
        - whether to continue to draw phase (bool)
    """
    logging.info("\n--- Pre-Draw Betting ---")

    # Use betting module to handle betting round
    new_pot, side_pots = betting.handle_betting_round(
        players=players,
        pot=pot,
        dealer_index=dealer_index,
        game_state=game_state,
        phase="pre-draw"
    )

    # Check if only one player remains
    active_players = [p for p in players if not p.folded]
    should_continue = len(active_players) > 1

    # If only one player remains, award them the pot
    if not should_continue:
        winner = active_players[0]
        winner.chips += new_pot
        logging.info(f"\n{winner.name} wins ${new_pot} (all others folded pre-draw)")

    return new_pot, side_pots, should_continue

def _log_chip_movements(players: List[Player], game_state: dict) -> None:
    """
    Log the chip movements from initial state.
    
    Args:
        players: List of players
        game_state: Game state containing initial chip counts
    """
    initial_chips = {
        p.name: next(
            player["chips"] 
            for player in game_state["players"] 
            if player["name"] == p.name
        )
        for p in players
    }
    
    for player in players:
        if player.chips != initial_chips[player.name]:
            net_change = player.chips - initial_chips[player.name]
            logging.info(
                f"{player.name}: ${initial_chips[player.name]} → ${player.chips} ({net_change:+d})"
            ) 