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
    """Handle the pre-draw betting round."""
    # Add dealer_index to game_state if not already present
    if game_state is None:
        game_state = {}
    game_state["dealer_index"] = dealer_index

    return betting.handle_betting_round(
        players=players,
        pot=pot,
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
