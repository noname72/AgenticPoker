from enum import Enum


class PlayerPosition(str, Enum):
    """Represents standard poker table positions."""

    DEALER = "dealer"
    SMALL_BLIND = "small_blind"
    BIG_BLIND = "big_blind"
    UNDER_THE_GUN = "under_the_gun"
    MIDDLE = "middle"
    CUTOFF = "cutoff"
    OTHER = "other"
