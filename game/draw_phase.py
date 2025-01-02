import logging
from typing import List

from .deck import Deck
from .player import Player


def handle_draw_phase(players: List[Player], deck: Deck) -> None:
    """
    Handle the draw phase where players can discard and draw new cards.

    Args:
        players: List of players in the game
        deck: The deck to draw new cards from
    """
    discarded_cards = []  # Track discarded cards for potential reshuffling

    for player in players:
        # Skip folded players
        if player.folded:
            continue

        # Get discard decisions from player
        discards = None
        if hasattr(player, "decide_draw"):
            try:
                discards = player.decide_draw()

                # Validate discard indexes
                if any(idx < 0 or idx >= 5 for idx in discards):
                    logging.info(f"{player.name} provided invalid discard indexes")
                    logging.info("Keeping current hand")
                    continue

            except Exception as e:
                logging.info(f"Error getting discard decision from {player.name}: {e}")
                logging.info("Keeping current hand")
                continue
        else:
            logging.info(
                "Non-AI player or player without decision method; keeping current hand"
            )
            continue

        # Handle discards and drawing new cards
        if discards:
            logging.info(f"{player.name} discarding positions: {discards}")

            # Remove discarded cards and add new ones
            discarded = [player.hand.cards[idx] for idx in discards]
            discarded_cards.extend(discarded)
            player.hand.remove_cards(discards)

            # Reshuffle if needed
            if len(deck.cards) < len(discards):
                logging.info("Reshuffling discarded cards into deck")
                if discarded_cards:
                    deck.cards.extend(discarded_cards)
                    deck.shuffle()
                    discarded_cards = []

            # Draw new cards
            new_cards = deck.deal(len(discards))
            player.hand.add_cards(new_cards)
        else:
            logging.info("No cards discarded; keeping current hand")
