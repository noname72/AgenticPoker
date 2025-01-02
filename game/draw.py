import logging
from typing import List

from exceptions import InvalidActionError, PokerGameError

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
    for player in players:
        if player.folded:
            continue

        # Get discard decisions with better error handling
        discards = None
        if hasattr(player, "decide_draw"):
            try:
                discards = player.decide_draw()
                # Validate discard indexes
                if any(idx < 0 or idx >= 5 for idx in discards):
                    logging.warning(f"{player.name} invalid discard indexes")
                    logging.info(f"{player.name} keeping current hand")
                    discards = None  # Reset discards to keep current hand
                    continue  # Skip to next player instead of raising exception
            except InvalidActionError as e:
                logging.error(str(e))
                continue
            except PokerGameError as e:
                logging.error(f"Game error from {player.name} during draw phase: {e}")
                continue
            except Exception as e:
                # Log unexpected errors but still continue the game
                logging.error(
                    f"Unexpected error from {player.name} during draw phase: {e}"
                )
                continue
        else:
            logging.info(
                "Non-AI player or player without decision method; keeping current hand"
            )

        # Handle discards and drawing new cards
        if discards:
            logging.info(
                f"Draw phase: {player.name} discarding {len(discards)} cards at positions: {discards}"
            )

            # Remove discarded cards and add to deck's discard pile
            discarded = [player.hand.cards[idx] for idx in discards]
            deck.add_discarded(discarded)  # Use deck's discard tracking
            player.hand.remove_cards(discards)

            # Reshuffle if needed
            if len(deck.cards) < len(discards):
                logging.info("Reshuffling discarded cards into deck")
                deck.reshuffle_discards()  # Use deck's reshuffle method

            # Draw new cards
            new_cards = deck.deal(len(discards))
            player.hand.add_cards(new_cards)
        else:
            if discards is not None:  # Player explicitly chose to keep cards
                logging.info("No cards discarded; keeping current hand")
            else:  # Player had invalid indexes
                logging.info(f"{player.name} keeping current hand")
