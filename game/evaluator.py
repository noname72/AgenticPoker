from typing import List, NamedTuple

from .card import Card
from data.types.hand_rank import HandRank


class HandEvaluation(NamedTuple):
    """
    A named tuple containing the evaluation of a poker hand.

    Attributes:
        rank (HandRank): The rank of the hand (HIGH_CARD to ROYAL_FLUSH)
        tiebreakers (List[int]): Tiebreaker values in descending order of importance
        description (str): Human readable description of the hand
    """

    rank: HandRank
    tiebreakers: List[int]
    description: str


def evaluate_hand(cards: List[Card]) -> HandEvaluation:
    """
    Evaluate a 5-card poker hand and return its ranking, tiebreakers, and description.

    Args:
        cards (List[Card]): A list of exactly 5 Card objects representing a poker hand.

    Returns:
        HandEvaluation: A named tuple containing:
            - HandRank: Hand rank from HIGH_CARD to ROYAL_FLUSH
            - List[int]: Tiebreaker values in descending order of importance
            - str: Human readable description of the hand

    Hand Rankings (from best to worst):
        1. Royal Flush     - A, K, Q, J, 10 of the same suit
        2. Straight Flush  - Five sequential cards of the same suit
        3. Four of a Kind  - Four cards of the same rank
        4. Full House      - Three of a kind plus a pair
        5. Flush          - Any five cards of the same suit
        6. Straight       - Five sequential cards of mixed suits
        7. Three of a Kind - Three cards of the same rank
        8. Two Pair       - Two different pairs
        9. One Pair       - One pair of matching cards
        10. High Card     - Highest card when no other hand is made

    Note: This implementation uses a reversed ranking system where lower numbers
    indicate better hands (1 is best, 10 is worst).

    Raises:
        ValueError: If the hand doesn't contain exactly 5 cards

    Example:
        >>> hand = [Card('A', '♠'), Card('K', '♠'), Card('Q', '♠'), Card('J', '♠'), Card('10', '♠')]
        >>> evaluate_hand(hand)
        (1, [14, 13, 12, 11, 10], 'Royal Flush')
    """
    if len(cards) != 5:
        raise ValueError("Hand must contain exactly 5 cards")

    # Check for duplicate cards
    seen_cards = set()
    for card in cards:
        card_tuple = (card.rank, card.suit)
        if card_tuple in seen_cards:
            raise ValueError(f"Duplicate card found: {card}")
        seen_cards.add(card_tuple)

    # Convert face cards to numeric values (J=11, Q=12, K=13, A=14)
    values = {
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
        "10": 10,
        "J": 11,
        "Q": 12,
        "K": 13,
        "A": 14,
    }

    # Convert all ranks to numeric values using the values dictionary
    ranks = [values[str(card.rank).upper()] for card in cards]
    suits = [card.suit for card in cards]

    # Count occurrences of each rank
    rank_counts = {}
    for rank in ranks:
        rank_counts[rank] = rank_counts.get(rank, 0) + 1

    # Sort ranks by frequency (most frequent first), then by rank value (highest first)
    sorted_counts = sorted(
        rank_counts.items(),
        key=lambda x: (-x[1], -x[0]),  # Sort by count desc, then rank desc
    )

    # Sort ranks in descending order for high card comparisons
    ranks = sorted(ranks, reverse=True)

    # Check for straight and flush
    is_flush = len(set(suits)) == 1
    is_straight = len(rank_counts) == 5 and max(ranks) - min(ranks) == 4

    # Special case: Ace-low straight (A,2,3,4,5)
    if set(ranks) == {14, 2, 3, 4, 5}:
        is_straight = True
        ranks = [5, 4, 3, 2, 1]  # Ace counts as low in this case

    # Determine hand rank and tiebreakers
    if is_flush and is_straight:
        if ranks[0] == 14:  # Ace high
            return HandEvaluation(HandRank.ROYAL_FLUSH, ranks, "Royal Flush")
        return HandEvaluation(HandRank.STRAIGHT_FLUSH, ranks, f"Straight Flush, {ranks[0]} high")

    elif sorted_counts[0][1] == 4:  # Four of a kind
        quad_rank = sorted_counts[0][0]
        kicker = sorted_counts[1][0]
        return HandEvaluation(HandRank.FOUR_OF_KIND, [quad_rank, kicker], f"Four of a Kind, {quad_rank}s")

    elif sorted_counts[0][1] == 3 and sorted_counts[1][1] == 2:  # Full house
        trips_rank = sorted_counts[0][0]
        pair_rank = sorted_counts[1][0]
        return HandEvaluation(
            HandRank.FULL_HOUSE,
            [trips_rank, pair_rank],
            f"Full House, {trips_rank}s over {pair_rank}s"
        )

    elif is_flush:
        return HandEvaluation(HandRank.FLUSH, ranks, f"Flush, {ranks[0]} high")

    elif is_straight:
        return HandEvaluation(HandRank.STRAIGHT, ranks, f"Straight, {ranks[0]} high")

    elif sorted_counts[0][1] == 3:  # Three of a kind
        trips_rank = sorted_counts[0][0]
        kickers = sorted([r for r in ranks if r != trips_rank], reverse=True)
        return HandEvaluation(HandRank.THREE_OF_KIND, [trips_rank] + kickers, f"Three of a Kind, {trips_rank}s")

    elif sorted_counts[0][1] == 2 and sorted_counts[1][1] == 2:  # Two pair
        high_pair = sorted_counts[0][0]
        low_pair = sorted_counts[1][0]
        kicker = sorted_counts[2][0]
        return HandEvaluation(
            HandRank.TWO_PAIR,
            [high_pair, low_pair, kicker],
            f"Two Pair, {high_pair}s and {low_pair}s"
        )

    elif sorted_counts[0][1] == 2:  # One pair
        pair_rank = sorted_counts[0][0]
        # Sort remaining cards by rank for kickers
        kickers = sorted([r for r in ranks if r != pair_rank], reverse=True)[:3]
        return HandEvaluation(
            HandRank.ONE_PAIR,
            [pair_rank] + kickers,
            f"One Pair, {_rank_to_name(pair_rank)}s"
        )

    else:  # High card
        return HandEvaluation(HandRank.HIGH_CARD, ranks, f"High Card, {ranks[0]}")


def _rank_to_name(rank: int) -> str:
    """Convert numeric rank to card name."""
    names = {
        14: "Ace",
        13: "King", 
        12: "Queen",
        11: "Jack",
        10: "10"
    }
    return names.get(rank, str(rank))
