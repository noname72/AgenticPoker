import logging
from typing import List

from .player import Player
from .deck import Deck

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
        logging.info(f"\n{player.name}'s hand: {player.hand.show()}")
        
        # Get discards if player has a decision method
        if hasattr(player, "decide_draw"):
            discards = player.decide_draw()
            
            if discards and len(discards) <= 5:
                # Remove discarded cards and track them
                discarded = []
                for idx in sorted(discards, reverse=True):
                    card = player.hand.cards.pop(idx)
                    discarded.append(card)
                discarded_cards.extend(reversed(discarded))
                
                # Check if we need to reshuffle
                if len(deck.cards) < len(discards):
                    logging.info("Reshuffling discarded cards into deck")
                    deck.cards.extend(discarded_cards)
                    deck.shuffle()
                    discarded_cards = []
                
                # Draw new cards
                new_cards = deck.deal(len(discards))
                
                # Insert new cards at original positions
                for i, card in zip(sorted(discards), new_cards):
                    player.hand.cards.insert(i, card)
                
                logging.info(f"{player.name} discards {len(discards)} and draws {len(new_cards)}")
                logging.info(f"New hand: {player.hand.show()}")
            else:
                logging.info("Keeping current hand")
        else:
            logging.info("Keeping current hand") 