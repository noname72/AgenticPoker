import logging
from typing import List

from .deck import Deck
from .player import Player


def handle_draw_phase(players: List[Player], deck: Deck) -> None:
    """
    Handle the draw phase where players can discard and draw new cards.

    Each non-folded player gets one opportunity to discard 0-5 cards and draw
    replacements. AI players use decide_draw() to choose discards, while non-AI
    players keep their current hand.

    Args:
        players: List of active players
        deck: Current deck of cards

    Side Effects:
        - Updates player hands
        - Logs draw actions
    """
    logging.info("\n--- Draw Phase ---")
    discarded_cards = []

    for player in players:
        if player.folded:
            continue

        # Log current hand
        logging.info(f"\n{player.name}'s turn to draw")
        logging.info(f"Current hand: {player.hand.show()}")

        # Get discards if player has a decision method
        if hasattr(player, "decide_draw"):
            discards = player.decide_draw()

            # Validate discards
            if not all(0 <= idx < len(player.hand.cards) for idx in discards):
                logging.warning(
                    f"{player.name} provided invalid discard indexes: {discards}"
                )
                logging.info("Keeping current hand")
                continue

            if len(discards) > 5:
                logging.warning(f"{player.name} attempted to discard more than 5 cards")
                logging.info("Keeping current hand")
                continue

            if discards:
                logging.info(f"{player.name} discarding positions: {discards}")
                logging.info(f"Discarding cards at positions: {discards}")

                # Capture the cards being discarded before removing them
                discarded = [player.hand.cards[idx] for idx in discards]
                discarded_cards.extend(discarded)

                # Remove discarded cards using Hand's remove_cards method
                player.hand.remove_cards(discards)

                # Check if we need to reshuffle
                if len(deck.cards) < len(discards):
                    if discarded_cards:
                        logging.info("Reshuffling discarded cards into deck")
                        deck.cards.extend(discarded_cards)
                        deck.shuffle()
                        discarded_cards = []
                    else:
                        logging.warning(
                            "Deck is empty and no discarded cards to reshuffle"
                        )
                        logging.info("Keeping current hand")
                        continue

                # Draw and add new cards using Hand's add_cards method
                new_cards = deck.deal(len(discards))
                player.hand.add_cards(new_cards)

                logging.info(
                    f"Drew {len(new_cards)} new cards: {', '.join(str(card) for card in new_cards)}"
                )
                logging.info(f"New hand: {player.hand.show()}")
            else:
                logging.info("No cards discarded; keeping current hand")
        else:
            logging.info(
                "Non-AI player or player without decision method; keeping current hand"
            )
