import logging
from typing import Any, Dict, List, Union, Optional

from data.model import Game
from game.player import Player


def log_chip_movements(
    players: List[Player],
    initial_chips: Union[Dict[Player, int], Dict[str, int], dict],
    handle_mocks: bool = False,
) -> None:
    """
    Log chip movements for players from their initial amounts.

    Args:
        players: List of players to check
        initial_chips: Dictionary of initial chip amounts (either by Player or name)
        handle_mocks: Whether to handle test mock objects
    """
    for player in players:
        try:
            initial = (
                initial_chips[player.name]
                if isinstance(next(iter(initial_chips)), str)
                else initial_chips[player]
            )

            if player.chips != initial:
                net_change = player.chips - initial
                logging.info(
                    f"{player.name}: ${initial} → ${player.chips} ({net_change:+d})"
                )
        except (TypeError, AttributeError) as e:
            if handle_mocks:
                logging.info(
                    f"{player.name}: Chip movement tracking skipped in test mode"
                )
            else:
                raise e


def get_min_bet(game: "Game") -> int:
    """Calculate the minimum allowed bet amount.

    Args:
        game: Current game state

    Returns:
        int: Minimum allowed bet amount
    """
    # If no current bet, use big blind as minimum
    if game.current_bet == 0:
        return game.big_blind

    # For raises, minimum is double the current bet
    return game.current_bet * 2


def validate_bet_amount(bet_amount: int, min_bet: int, max_bet: Optional[int] = None) -> int:
    """Validate and adjust bet amounts against game rules.

    Args:
        bet_amount (int): The proposed bet amount to validate
        min_bet (int): Minimum allowed bet size
        max_bet (Optional[int]): Maximum allowed bet size, if any

    Returns:
        int: The validated bet amount, adjusted if needed
    """
    if bet_amount < min_bet:
        logging.info(
            f"Bet amount {bet_amount} below minimum {min_bet}, adjusting to min_bet"
        )
        return min_bet
    
    if max_bet is not None and bet_amount > max_bet:
        logging.info(
            f"Bet amount {bet_amount} above maximum {max_bet}, adjusting to max_bet"
        )
        return max_bet
    
    return bet_amount
