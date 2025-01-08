from typing import List, Optional, Tuple

from data.types.game_state import GameState
from data.types.pot_types import SidePot

from . import betting
from .player import Player


def handle_pre_draw_betting(
    players: List[Player],
    pot: int,
    dealer_index: int,
    game_state: Optional[GameState] = None,
) -> Tuple[int, Optional[List[SidePot]], bool]:
    """
    Handle the pre-draw betting round.

    Args:
        players: List of players in the game
        pot: Current pot amount
        dealer_index: Index of the dealer
        game_state: Optional GameState object containing game state information

    Returns:
        Tuple containing:
        - int: New pot amount after betting
        - Optional[List[SidePot]]: List of side pots if any were created
        - bool: True if the game should continue to the draw phase
    """
    game_state = betting.create_or_update_betting_state(
        players=players,
        pot=pot,
        dealer_index=dealer_index,
        game_state=game_state,
        phase="pre_draw",
    )

    return betting.handle_betting_round(
        players=players,
        pot=pot,
        game_state=game_state,
    )
