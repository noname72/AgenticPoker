class PokerGameError(Exception):
    """Base exception for poker game errors."""

    pass


class LLMError(PokerGameError):
    """Raised when LLM query fails."""

    pass


class OpenAIError(LLMError):
    """Raised when OpenAI API call fails."""

    pass


class InvalidGameStateError(PokerGameError):
    """Raised when game state is invalid."""

    pass


class InvalidActionError(PokerGameError):
    """Raised when player action is invalid."""

    pass


class InsufficientFundsError(PokerGameError):
    """Raised when player doesn't have enough chips."""

    pass


class PlayerNotFoundError(PokerGameError):
    """Raised when player is not found."""

    pass


class GameNotFoundError(PokerGameError):
    """Raised when game is not found."""

    pass


class RoundNotFoundError(PokerGameError):
    """Raised when round is not found."""

    pass


class ResponseParsingError(LLMError):
    """Error parsing LLM response."""

    pass
