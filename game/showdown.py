from typing import Dict, List

from data.types.hand_rank import HandRank
from data.types.pot_types import SidePot
from loggers.showdown_logger import ShowdownLogger

from .player import Player
from .pot import Pot


def log_hand_comparison(
    winner: Player, loser: Player, winner_hand: str, loser_hand: str
) -> None:
    """
    Log the comparison of two players' hands in a clear, validated format.

    Args:
        winner: Player who won the comparison
        loser: Player who lost the comparison
        winner_hand: String description of winner's hand
        loser_hand: String description of loser's hand

    Raises:
        ValueError: If attempting to compare a hand against itself
    """
    if winner == loser:
        raise ValueError("Cannot compare a hand against itself")

    ShowdownLogger.log_hand_comparison(
        winner_name=winner.name,
        loser_name=loser.name,
        winner_hand=winner_hand,
        loser_hand=loser_hand,
    )


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

    # Get total pot - just use pot.pot since it already includes all bets
    total_pot = pot.pot

    # Handle single player case first (i.e. everyone else folded)
    if len(active_players) == 1:
        winner = active_players[0]
        winner.chips += total_pot
        ShowdownLogger.log_single_winner(winner.name, total_pot)
    else:
        # Multiple players - determine winner(s)
        winners = _evaluate_hands(active_players)
        if winners:
            split_amount = total_pot // len(winners)
            remainder = total_pot % len(winners)

            # Distribute split amount and remainder
            for i, winner in enumerate(winners):
                amount = split_amount
                if i < remainder:  # Add extra chip for remainder
                    amount += 1
                winner.chips += amount
                ShowdownLogger.log_pot_win(
                    winner.name, amount, is_split=(len(winners) > 1)
                )

    # Clear any remaining bets
    for player in players:
        player.bet = 0

    # Log final chip movements for all players
    for player in players:
        initial = initial_chips.get(
            player, player.chips
        )  # Default to current chips if not in initial_chips
        ShowdownLogger.log_chip_movements(player.name, initial, player.chips)


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

    # Log detailed hand evaluations for debugging
    for player in players:
        rank, tiebreakers, description = player.hand.evaluate()
        ShowdownLogger.log_hand_evaluation(
            player.name,
            [str(card) for card in player.hand.cards],
            description,
            rank,
            tiebreakers,
        )

    # Find best hand(s)
    best_players = [players[0]]
    best_hand = players[0].hand

    for player in players[1:]:
        comparison = player.hand.compare_to(best_hand)
        if comparison > 0:  # Current player has better hand
            best_players = [player]
            best_hand = player.hand
        elif comparison == 0:  # Tie
            best_players.append(player)

        # Log comparison with all required parameters
        _, _, player_desc = player.hand.evaluate()
        _, _, best_desc = best_hand.evaluate()

        # If comparison > 0, current player's hand is better
        # If comparison == 0, it's a tie
        # If comparison < 0, best_hand is better
        ShowdownLogger.log_hand_comparison(
            winner_name=best_players[0].name,  # Current best hand owner
            loser_name=player.name,  # Current player being compared
            comparison=comparison,
            winner_hand=best_desc,
            loser_hand=player_desc,
        )

    return best_players
