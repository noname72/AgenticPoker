from typing import List, Optional, Tuple

from . import betting
from .player import Player
from .types import SidePot


def handle_pre_draw_betting(
    players: List[Player],
    pot: int,
    dealer_index: int,
    game_state: Optional[dict] = None,
) -> Tuple[int, Optional[List[SidePot]], bool]:
    """
    Handle the pre-draw betting round.

    Args:
        players: List of players in the game
        pot: Current pot amount
        dealer_index: Index of the dealer
        game_state: Optional dictionary containing game state information

    Returns:
        Tuple containing:
        - int: New pot amount after betting
        - Optional[List[SidePot]]: List of side pots if any were created
        - bool: True if the game should continue to the draw phase
    """
    # Create a new game state dictionary or copy the existing one
    current_game_state = {} if game_state is None else game_state.copy()
    current_game_state["dealer_index"] = dealer_index
    current_game_state["first_bettor_index"] = (dealer_index + 1) % len(players)

    return betting.handle_betting_round(
        players=players,
        pot=pot,
        game_state=current_game_state,
    )
