from typing import Dict, List, TYPE_CHECKING, Tuple
import itertools

from data.types.hand_rank import HandRank
from data.types.pot_types import SidePot
from loggers.showdown_logger import ShowdownLogger
from loggers.game_logger import GameLogger # For logging warnings

from .player import Player
from .pot import Pot
from .card import Card
from .evaluator import evaluate_hand, HandEvaluation
from .hand import Hand # Import Hand for type hinting and operations

if TYPE_CHECKING:
    from .game import AgenticPoker # Forward reference for AgenticPoker


def log_hand_comparison(
    winner: Player, loser: Player, winner_hand_eval: HandEvaluation, loser_hand_eval: HandEvaluation
) -> None:
    """
    Log the comparison of two players' hands in a clear, validated format.

    Args:
        winner: Player who won the comparison
        loser: Player who lost the comparison
        winner_hand_eval: HandEvaluation object of winner's hand
        loser_hand_eval: HandEvaluation object of loser's hand

    Raises:
        ValueError: If attempting to compare a hand against itself
    """
    if winner == loser:
        raise ValueError("Cannot compare a hand against itself")

    ShowdownLogger.log_hand_comparison(
        winner_name=winner.name,
        loser_name=loser.name,
        winner_hand=winner_hand_eval.description, # Use description from HandEvaluation
        loser_hand=loser_hand_eval.description,  # Use description from HandEvaluation
        # TODO: The ShowdownLogger.log_hand_comparison might need an update
        # if it expects a 'comparison' parameter, or adjust this call.
        # For now, assuming it takes these string descriptions.
    )


def handle_showdown(game: "AgenticPoker") -> None:
    """
    Handle the showdown phase where winners are determined and pots are distributed.

    Args:
        game: The AgenticPoker game instance.

    Side Effects:
        - Updates player chip counts
        - Logs showdown results and chip movements
    """
    active_players = [p for p in game.table.players if not p.folded]
    initial_chips = game.initial_chips
    pot = game.pot

    ShowdownLogger.log_showdown_start()

    for player in active_players:
        if game.game_type == "TEXAS_HOLDEM":
            if len(game.community_cards) < 5:
                GameLogger.log_warning(
                    f"Showdown for {player.name} in TEXAS_HOLDEM with < 5 community cards ({len(game.community_cards)}). Evaluating based on available cards."
                )
                # Potentially, evaluate with what's available or just hole cards if board is too short.
                # For now, we'll proceed, and evaluate_hand will handle it if total cards < 5.
            
            if not player.hand or not player.hand.cards: # Ensure player has hole cards
                 GameLogger.log_warning(f"Player {player.name} has no hole cards for Texas Hold'em showdown. Skipping.")
                 player.best_hand_evaluation = None # Or a very low ranking hand
                 continue

            hole_cards = player.hand.cards
            all_cards = hole_cards + game.community_cards
            
            if len(all_cards) < 5:
                GameLogger.log_warning(f"Player {player.name} has fewer than 5 cards ({len(all_cards)}) to evaluate for Texas Hold'em. Skipping.")
                player.best_hand_evaluation = Hand(cards=all_cards).evaluate() if all_cards else Hand().evaluate() # Evaluate whatever they have or empty
            else:
                best_player_hand_eval = None
                all_5_card_combinations = itertools.combinations(all_cards, 5)
                
                for combo_cards in all_5_card_combinations:
                    # Create a temporary Hand object for evaluation
                    temp_hand = Hand()
                    temp_hand.add_cards(list(combo_cards)) # add_cards expects a list
                    current_eval = temp_hand.evaluate()

                    if best_player_hand_eval is None or current_eval > best_player_hand_eval:
                        best_player_hand_eval = current_eval
                
                player.best_hand_evaluation = best_player_hand_eval

            if player.best_hand_evaluation:
                # TODO: Add ShowdownLogger.log_player_texas_holdem_hand_evaluation(player_name, best_hand_description, hole_cards, community_cards)
                ShowdownLogger.log_player_hand(
                    player.name, 
                    f"{player.best_hand_evaluation.description} (Hole: {', '.join(map(str, hole_cards))})"
                )
            else:
                 ShowdownLogger.log_player_hand(player.name, "Could not evaluate hand.")

        elif game.game_type == "FIVE_CARD_DRAW":
            if player.hand and player.hand.cards:
                player.best_hand_evaluation = player.hand.evaluate()
                ShowdownLogger.log_player_hand(player.name, player.best_hand_evaluation.description)
            else:
                GameLogger.log_warning(f"Player {player.name} has no hand for Five Card Draw showdown. Skipping.")
                player.best_hand_evaluation = Hand().evaluate() # Empty hand evaluation
        else:
            GameLogger.log_warning(f"Unknown game type {game.game_type} in showdown. Skipping hand evaluation for {player.name}.")
            player.best_hand_evaluation = Hand().evaluate() # Empty hand evaluation


    total_pot_value = pot.get_total_pot() # Assuming pot.get_total_pot() sums main and side pots

    if len(active_players) == 1:
        winner = active_players[0]
        winner.chips += total_pot_value
        ShowdownLogger.log_single_winner(winner.name, total_pot_value)
    else:
        # Filter out players who couldn't form a hand (e.g. no cards in TH)
        eligible_players = [p for p in active_players if p.best_hand_evaluation is not None and p.best_hand_evaluation.rank != HandRank.UNKNOWN]
        if not eligible_players:
            GameLogger.log_warning("No eligible players for showdown after hand evaluation.")
            # This case might need specific handling, e.g., return pot to players or split if all had bad hands.
            # For now, let's assume if no one has a valid hand, the pot might be split or handled by specific rules.
            # Or, if this implies an error, it should be logged.
        else:
            winners = _determine_winners_from_evaluations(eligible_players)
            if winners:
                # Pot distribution logic (simplified, assumes single pot for now, needs side pot integration)
                # This part needs to be carefully reviewed and potentially use pot.distribute(winners)
                # which should handle side pots correctly.
                # For now, a simple split of the total pot for demonstration.
                
                # TODO: Integrate with Pot.distribute() which should handle side pots
                # pot.distribute_pots(winners) # This is the ideal call
                
                # Simplified distribution for now:
                split_amount = total_pot_value // len(winners)
                remainder = total_pot_value % len(winners)
                for i, winner in enumerate(winners):
                    amount_won = split_amount + (1 if i < remainder else 0)
                    winner.chips += amount_won
                    ShowdownLogger.log_pot_win(
                        winner.name, amount_won, is_split=(len(winners) > 1)
                    )
            else:
                GameLogger.log_warning("No winners determined from showdown evaluations.")


    for player in game.table.players: # Reset bets for all players on table
        player.bet = 0

    for player in game.table.players:
        initial = initial_chips.get(player, player.chips)
        ShowdownLogger.log_chip_movements(player.name, initial, player.chips)


def _determine_winners_from_evaluations(evaluated_players: List[Player]) -> List[Player]:
    """
    Evaluate player hands (using player.best_hand_evaluation) to determine winner(s).

    Args:
        evaluated_players: List of players who have their best_hand_evaluation set.

    Returns:
        List[Player]: List of winning players (multiple in case of tie)
    """
    if not evaluated_players:
        return []

    # Log detailed hand evaluations for debugging
    for player in evaluated_players:
        if player.best_hand_evaluation:
            ShowdownLogger.log_hand_evaluation( # Assuming this logger method exists and is suitable
                player.name,
                # TODO: ShowdownLogger.log_hand_evaluation might need adjustment
                # if it expects raw cards. Here we pass the description.
                # Or, we might need to log the cards that formed the best hand.
                cards_str_list = [str(c) for c in player.hand.cards], # This shows hole cards for TH, or full hand for 5CD
                description=player.best_hand_evaluation.description,
                rank=player.best_hand_evaluation.rank,
                tie_breakers=player.best_hand_evaluation.tie_breakers
            )

    best_players = [evaluated_players[0]]
    # best_evaluation is now an HandEvaluation object
    best_evaluation = evaluated_players[0].best_hand_evaluation 

    for player in evaluated_players[1:]:
        current_player_eval = player.best_hand_evaluation
        if not current_player_eval: # Skip if player has no evaluation
            continue

        # HandEvaluation objects are comparable directly
        if current_player_eval > best_evaluation:
            best_players = [player]
            best_evaluation = current_player_eval
        elif current_player_eval == best_evaluation: # Tie
            best_players.append(player)
        
        # Log comparison using the log_hand_comparison function
        # Determine who is winner and loser for this specific comparison log entry
        comparison_winner = player if current_player_eval >= best_evaluation else best_players[0]
        comparison_loser = best_players[0] if current_player_eval >= best_evaluation else player
        
        # Ensure we don't log comparison if they are the same player in case of a new best_player
        if comparison_winner != comparison_loser :
             log_hand_comparison(
                 winner=comparison_winner, 
                 loser=comparison_loser, 
                 winner_hand_eval=comparison_winner.best_hand_evaluation, 
                 loser_hand_eval=comparison_loser.best_hand_evaluation
            )


    return best_players
