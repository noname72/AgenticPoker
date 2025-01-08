from pydantic import BaseModel


class DeckState(BaseModel):
    """Represents the state of the deck."""

    cards_remaining: int
