from enum import Enum, auto

class HandRank(Enum):
    """
    Poker hand rankings from weakest (HIGH_CARD) to strongest (ROYAL_FLUSH).
    Higher numerical values represent stronger hands.
    """
    HIGH_CARD = 1
    ONE_PAIR = 2
    TWO_PAIR = 3
    THREE_OF_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10

    def __lt__(self, other):
        if not isinstance(other, HandRank):
            return NotImplemented
        return self.value < other.value

    def __str__(self):
        return self.name.replace('_', ' ').title() 