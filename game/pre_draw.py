import logging
from typing import Dict, List, Optional, Tuple

from .player import Player
from .types import SidePot
from . import betting
from .pot_manager import PotManager

def handle_pre_draw_betting(
    players: List[Player],
    pot: int,
    dealer_index: int,
    game_state: dict,
    pot_manager: 'PotManager'
) -> Tuple[int, Optional[List[SidePot]], bool]:
    """
    Handle the pre-draw betting round.

    Args:
        players: List of active players
        pot: Current pot amount
        dealer_index: Position of the dealer
        game_state: Current game state dictionary
        pot_manager: PotManager instance handling pot calculations

    Returns:
        Tuple containing:
        - Updated pot amount
        - List of side pots (if any) or None
        - Boolean indicating if more than one player remains (True if game should continue)
    """
    new_pot, side_pots = betting.handle_betting_round(
        players,
        pot,
        dealer_index,
        game_state,
        phase="pre-draw"
    )
    
    # Check if only one player remains
    active_players = [p for p in players if not p.folded]
    should_continue = len(active_players) > 1
    
    if not should_continue:
        # Award pot to last remaining player
        winner = active_players[0]
        winner.chips += new_pot
        logging.info(f"\n{winner.name} wins ${new_pot} (all others folded pre-draw)")
        _log_chip_movements(players, game_state)
    
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