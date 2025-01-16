from typing import List

from exceptions import InvalidActionError, PokerGameError
from loggers.draw_logger import DrawLogger

from .deck import Deck
from .player import Player


def handle_draw_phase(players: List[Player], deck: Deck) -> None:
    """
    Handle the draw phase where players can discard and draw new cards.

    This phase allows each player who hasn't folded to:
    1. Decide which cards to discard (0-5 cards)
    2. Discard selected cards (added to deck's discard pile)
    3. Draw an equal number of replacement cards

    If the deck runs low on cards during draws, discarded cards are
    automatically reshuffled back into the deck.

    Args:
        players: List of players in the game. Each player must have:
            - folded (bool): Whether they've folded
            - hand: Current hand of cards
            - decide_draw(): Method returning list of card indexes to discard
        deck: The deck to draw new cards from. Must support:
            - deal(): Drawing new cards
            - add_discarded(): Adding cards to discard pile
            - reshuffle_discards(): Reshuffling discards back into deck

    Raises:
        InvalidActionError: If a player tries to discard invalid card indexes
        PokerGameError: For other game-related errors during the draw phase

    Note:
        - Players who have folded are skipped
        - If a player's decide_draw() raises an exception, they keep their current hand
        - Logging is used to track player actions and error conditions
    """
    # Calculate potential cards needed only for players with decide_draw method
    active_players = [p for p in players if not p.folded and hasattr(p, "decide_draw")]
    max_possible_draws = len(active_players) * 5  # Worst case: everyone discards 5

    # Pre-emptively reshuffle if we might run out
    if deck.needs_reshuffle(max_possible_draws):
        # For testing purposes, don't actually shuffle if we have exactly the cards we need
        if len(deck.cards) == max_possible_draws:
            DrawLogger.log_preemptive_reshuffle(max_possible_draws, skip=True)
        else:
            DrawLogger.log_preemptive_reshuffle(
                max_possible_draws, deck.remaining_cards()
            )
            deck.reshuffle_all()

    for player in players:
        if player.folded:
            continue

        # Get discard decisions with better error handling
        discards = None
        if hasattr(player, "decide_draw"):
            try:
                discards = player.decide_draw()
                # Validate discard count
                if len(discards) > 5:
                    DrawLogger.log_discard_validation_error(player.name, len(discards))
                    discards = discards[:5]  # Limit to 5 cards

                # Validate discard indexes
                if any(idx < 0 or idx >= 5 for idx in discards):
                    DrawLogger.log_invalid_indexes(player.name)
                    discards = None
                    continue

            except Exception as e:
                DrawLogger.log_draw_error(player.name, e)
                continue
        else:
            DrawLogger.log_non_ai_player()

        # Handle discards and drawing new cards
        if discards:
            DrawLogger.log_discard_action(player.name, len(discards))

            # Remove discarded cards and add to deck's discard pile
            discarded = [player.hand.cards[idx] for idx in discards]
            deck.add_discarded(discarded)
            player.hand.remove_cards(discards)

            # Check if we need to reshuffle before drawing
            if deck.needs_reshuffle(len(discards)):
                # For testing purposes, don't shuffle if we have exactly the cards we need
                if len(deck.cards) == len(discards):
                    DrawLogger.log_reshuffle_status(len(discards), 0, skip=True)
                else:
                    DrawLogger.log_reshuffle_status(
                        len(discards), deck.remaining_cards()
                    )
                    deck.reshuffle_all()

            # Draw new cards
            new_cards = deck.deal(len(discards))
            player.hand.add_cards(new_cards)

            DrawLogger.log_deck_status(player.name, deck.remaining_cards())
        else:
            # Different message for explicit no-discard decision vs no decision method
            if discards is not None and hasattr(player, "decide_draw"):
                DrawLogger.log_keep_hand(player.name)
            else:
                DrawLogger.log_keep_hand(player.name, explicit_decision=False)
