from collections import Counter
from typing import List, Tuple

from .card import Card


def evaluate_hand(cards: List[Card]) -> Tuple[int, List[int], str]:
    """
    Evaluate the strength of a five-card poker hand.

    Args:
        cards (List[Card]): A list of exactly five Card objects representing a poker hand.

    Returns:
        Tuple[int, List[int], str]: A tuple containing:
            - int: Hand rank (1-10, where 1 is the best possible hand)
            - List[int]: Relevant card values for breaking ties, in order of importance
            - str: Human-readable description of the hand (e.g., "Full House")

    Hand Rankings (from strongest to weakest):
        1. Royal Flush
        2. Straight Flush
        3. Four of a Kind
        4. Full House
        5. Flush
        6. Straight
        7. Three of a Kind
        8. Two Pair
        9. One Pair
        10. High Card

    Note:
        Ace (14) can be used as both high (A-K-Q-J-10) and low (5-4-3-2-A) in straights.
    """
    rank_values = {str(r): r for r in range(2, 11)}
    rank_values.update({"J": 11, "Q": 12, "K": 13, "A": 14})

    ranks = sorted([rank_values[str(card.rank)] for card in cards], reverse=True)
    suits = [card.suit for card in cards]

    rank_counts = Counter(ranks)
    sorted_counts = sorted(rank_counts.items(), key=lambda x: (-x[1], -x[0]))

    is_flush = len(set(suits)) == 1
    is_straight = len(rank_counts) == 5 and (ranks[0] - ranks[-1] == 4)

    if set(ranks) == {14, 5, 4, 3, 2}:
        is_straight = True
        ranks = [5, 4, 3, 2, 1]

    if is_flush and is_straight:
        if ranks[0] == 14:
            return (1, ranks, "Royal Flush")
        return (2, ranks, "Straight Flush")
    elif sorted_counts[0][1] == 4:
        return (3, [sorted_counts[0][0], sorted_counts[1][0]], "Four of a Kind")
    elif sorted_counts[0][1] == 3 and sorted_counts[1][1] == 2:
        return (4, [sorted_counts[0][0], sorted_counts[1][0]], "Full House")
    elif is_flush:
        return (5, ranks, "Flush")
    elif is_straight:
        return (6, ranks, "Straight")
    elif sorted_counts[0][1] == 3:
        return (7, [sorted_counts[0][0]] + ranks, "Three of a Kind")
    elif sorted_counts[0][1] == 2 and sorted_counts[1][1] == 2:
        return (
            8,
            [sorted_counts[0][0], sorted_counts[1][0], sorted_counts[2][0]],
            "Two Pair",
        )
    elif sorted_counts[0][1] == 2:
        return (9, [sorted_counts[0][0]] + ranks, "One Pair")
    else:
        return (10, ranks, "High Card")
