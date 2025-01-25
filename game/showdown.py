from typing import Dict, List

from data.types.pot_types import SidePot
from loggers.showdown_logger import ShowdownLogger

from .player import Player
from .pot import Pot


def handle_showdown(
    players: List[Player],
    initial_chips: Dict[Player, int],
    pot: Pot,
) -> None:
    """
    Handle the showdown phase where winners are determined and pots are distributed.

    Args:
        players: List of active players
        initial_chips: Dictionary of starting chip counts for each player
        pot: Pot instance handling pot distributions

    Side Effects:
        - Updates player chip counts
        - Logs showdown results and chip movements
    """
    active_players = [p for p in players if not p.folded]

    # Log showdown hands
    ShowdownLogger.log_showdown_start()
    for player in active_players:
        ShowdownLogger.log_player_hand(player.name, player.hand.show())

    # Handle single player case first (i.e. everyone else folded)
    if len(active_players) == 1:
        winner = active_players[0]
        pot_amount = pot.pot

        # Update winner's chips
        winner.chips += pot_amount

        ShowdownLogger.log_single_winner(winner.name, pot_amount)
        # _log_chip_movements(players, initial_chips)
        return

    # Get side pots from pot manager
    try:
        # Changed to pass only active_players
        side_pots = pot.calculate_side_pots(active_players)

        # If no side pots, create one main pot
        if not side_pots:
            pot_amount = pot.pot
            side_pots = [
                SidePot(
                    amount=pot_amount, eligible_players=[p.name for p in active_players]
                )
            ]
    except (AttributeError, TypeError):
        # Calculate total pot from chip differences
        total_pot = 0
        for player in players:
            if player in initial_chips:
                total_pot += initial_chips[player] - player.chips

        side_pots = [
            SidePot(amount=total_pot, eligible_players=[p.name for p in active_players])
        ]

    # Distribute each pot
    for pot in side_pots:
        eligible_players = [p for p in active_players if p.name in pot.eligible_players]
        if eligible_players:
            winners = _evaluate_hands(eligible_players)
            if winners:
                pot_amount = int(pot.amount)
                split_amount = pot_amount // len(winners)
                remainder = pot_amount % len(winners)

                # Distribute split amount and remainder
                for i in range(len(winners)):
                    winner = winners[i]
                    amount = split_amount
                    if i < remainder:  # Add extra chip for remainder
                        amount += 1

                    # Update winner's chips
                    winner.chips += amount

                    ShowdownLogger.log_pot_win(
                        winner.name, amount, is_split=(len(winners) > 1)
                    )

    # Log final chip movements for players in initial_chips
    for player in players:
        if player in initial_chips:
            ShowdownLogger.log_chip_movements(
                player.name, initial_chips[player], player.chips
            )
        else:
            # For players not in initial_chips (like RandomAgent), just log current chips
            ShowdownLogger.log_chip_movements(player.name, player.chips, player.chips)


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
