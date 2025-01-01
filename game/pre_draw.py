import logging
from typing import List, Optional, Tuple

from . import betting
from .player import Player
from .pot_manager import PotManager
from .types import SidePot


def handle_pre_draw_betting(
    players: List[Player],
    pot: int,
    dealer_index: int,
    game_state: Optional[dict] = None,
) -> Tuple[int, Optional[List[SidePot]], bool]:
    """Handle the pre-draw betting round.
    
    Args:
        players: List of active players
        pot: Current pot amount
        dealer_index: Position of the dealer
        game_state: Optional game state dictionary
        
    Returns:
        Tuple containing:
        - new pot amount
        - list of side pots (if any)
        - boolean indicating if game should continue
    """
    return betting.handle_betting_round(
        players=players,
        current_bet=game_state.get("current_bet", 0) if game_state else 0,
        pot=pot,
        dealer_index=dealer_index,
        game_state=game_state,
    )


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
