from typing import TYPE_CHECKING, List, Optional, Tuple

from data.types.pot_types import SidePot

from . import betting

if TYPE_CHECKING:
    from game.game import Game

#! is this module needed if all it does is call handle_betting_round????
def handle_pre_draw_betting(
    game: "Game",
) -> Tuple[int, Optional[List[SidePot]], bool]:
    """
    Handle the pre-draw betting round.

    Args:
        game: Game object

    Returns:
        Tuple containing:
        - int: New pot amount after betting
        - Optional[List[SidePot]]: List of side pots if any were created
        - bool: True if the game should continue to the draw phase
    """
    return betting.handle_betting_round(game)
