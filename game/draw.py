from typing import TYPE_CHECKING, List

from loggers.draw_logger import DrawLogger

from .deck import Deck
from .player import Player

if TYPE_CHECKING:
    from game.game import Game

MAX_DISCARD = 5


def handle_draw_phase(game: "Game") -> None:
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

    # First, figure out how many cards might possibly be drawn.
    active_players = [
        p for p in game.players if not p.folded and hasattr(p, "decide_discard")
    ]
    max_possible_draws = len(active_players) * MAX_DISCARD

    handle_preemptive_reshuffle(game.deck, max_possible_draws)

    # Process each player's draw
    for player in game.players:
        if player.folded:
            continue

        # Get discard decisions, if possible.
        discard_indices = get_discard_indices(player)
        if discard_indices is None:
            # This means the player either doesn't have decide_draw or we hit an error
            # in deciding discards. We skip discarding/drawing but still log accordingly.
            DrawLogger.log_keep_hand(
                player.name,
                explicit_decision=(
                    False if not hasattr(player, "decide_discard") else True
                ),
            )
            continue

        # Perform discarding logic if the player actually wants to discard.
        if discard_indices:
            process_discard_and_draw(player, game.deck, discard_indices)
        else:
            # The player explicitly decided to keep the entire hand (no discard).
            DrawLogger.log_keep_hand(player.name, explicit_decision=True)


def handle_preemptive_reshuffle(deck: Deck, needed_cards: int) -> None:
    """
    Checks if a reshuffle is needed before drawing cards and performs it if necessary.
    Skips reshuffling if we have exactly the number of cards needed.

    Args:
        deck: The deck to potentially reshuffle
        needed_cards: Number of cards that might be needed
    """
    if deck.needs_reshuffle(needed_cards):
        if len(deck.cards) == needed_cards:
            DrawLogger.log_preemptive_reshuffle(needed_cards, skip=True)
        else:
            DrawLogger.log_preemptive_reshuffle(needed_cards, deck.remaining_cards())
            deck.reshuffle_all()


def get_discard_indices(player: Player) -> List[int] | None:
    """
    Helper to safely get the discard indices from a player.

    Returns:
        A list of valid discard indices or None if invalid/unavailable.
    """
    if not hasattr(player, "decide_discard"):
        # If the player has no AI or method for deciding, return None so we skip.
        DrawLogger.log_non_ai_player()
        return None

    try:
        discards = player.decide_discard()
        if len(discards) > MAX_DISCARD:
            # Log and trim if too many discards
            DrawLogger.log_discard_validation_error(player.name, len(discards))
            discards = discards[:MAX_DISCARD]

        # Validate all indices are between 0 and 4 (assuming 5-card hands).
        if any(idx < 0 or idx >= 5 for idx in discards):
            DrawLogger.log_invalid_indexes(player.name)
            return None

        return discards

    except Exception as e:
        # If there's an error in decide_draw, we log and return None so the player keeps the hand.
        DrawLogger.log_draw_error(player.name, e)
        return None


def process_discard_and_draw(
    player: Player, deck: Deck, discard_indices: List[int]
) -> None:
    """
    Removes the given indices from the player's hand, reshuffles if necessary,
    and deals new cards to match the discard count.
    """
    discard_count = len(discard_indices)
    DrawLogger.log_discard_action(player.name, discard_count)

    # Get the actual card objects and remove them from the player's hand
    discarded_cards = [player.hand.cards[idx] for idx in discard_indices]
    deck.add_discarded(discarded_cards)
    player.hand.remove_cards(discard_indices)

    # Check if we need to reshuffle before drawing
    if deck.needs_reshuffle(discard_count):
        if len(deck.cards) == discard_count:
            DrawLogger.log_reshuffle_status(discard_count, 0, skip=True)
        else:
            DrawLogger.log_reshuffle_status(discard_count, deck.remaining_cards())
            deck.reshuffle_all()

    # Draw new cards to replace the discarded ones
    new_cards = deck.deal(discard_count)
    player.hand.add_cards(new_cards)

    # Log the deck status
    DrawLogger.log_deck_status(player.name, deck.remaining_cards())
