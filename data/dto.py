from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PlayerStatsDTO(BaseModel):
    """Data Transfer Object for player statistics.

    Tracks various performance metrics and statistics for a player across all games,
    including win rates, earnings, and betting patterns.
    """

    games_played: int = Field(default=0, description="Total number of games played")
    hands_won: int = Field(default=0, description="Total number of hands won")
    total_winnings: int = Field(default=0, description="Total amount of chips won")
    largest_pot: int = Field(default=0, description="Largest pot won in a single hand")
    total_time_played: int = Field(
        default=0, description="Total time played in seconds"
    )
    bluff_success_rate: float = Field(
        default=0.0, description="Rate of successful bluffs"
    )
    avg_bet_size: float = Field(default=0.0, description="Average bet size")

    class Config:
        from_attributes = True


class PlayerDTO(BaseModel):
    """Data Transfer Object for player information.

    Contains core player data including identification, display name, and associated statistics.
    Used for transferring player information between different parts of the application.
    """

    id: Optional[int] = None
    name: str = Field(..., description="Player's display name")
    created_at: datetime = Field(default_factory=datetime.now)
    stats: Optional[PlayerStatsDTO] = None

    class Config:
        from_attributes = True


class GamePlayerAssociationDTO(BaseModel):
    """Data Transfer Object for player's game session state.

    Represents the current state of a player within a specific game, including their
    chip count, betting status, and current hand. This DTO maintains the relationship
    between players and games.
    """

    id: Optional[int] = None
    game_id: int
    player_id: int
    chips: int = Field(default=1000, description="Current chip count")
    folded: bool = Field(default=False, description="Whether player has folded")
    bet: int = Field(default=0, description="Current bet amount")
    current_hand: Optional[str] = None

    class Config:
        from_attributes = True


class RoundActionDTO(BaseModel):
    """Data Transfer Object for player actions during a game round.

    Captures detailed information about each action a player takes during a round,
    including the type of action, timing, and AI-related metrics like confidence
    scores and decision factors.
    """

    id: Optional[int] = None
    round_id: int
    association_id: int
    action_type: str = Field(
        ..., description="Type of action (fold, call, raise, etc.)"
    )
    amount: int = Field(default=0, description="Amount of chips for bets/raises")
    timestamp: datetime = Field(default_factory=datetime.now)
    confidence_score: Optional[float] = None
    decision_factors: Optional[Dict] = None
    processing_time: Optional[float] = None

    class Config:
        from_attributes = True


class RoundDTO(BaseModel):
    """Data Transfer Object for a poker game round.

    Represents a single round of poker, tracking the community cards, pot size,
    player actions, and round outcomes. Includes support for side pots and
    winning hand information.
    """

    id: Optional[int] = None
    game_id: int
    round_number: int = Field(default=1)
    pot: int = Field(default=0)
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    community_cards: Optional[str] = None
    winning_hand: Optional[str] = None
    side_pots: Optional[Dict] = None
    actions: List[RoundActionDTO] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ChatMessageDTO(BaseModel):
    """DTO for chat messages."""

    id: Optional[int] = None
    game_id: int
    player_id: int
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class GameSnapshotDTO(BaseModel):
    """DTO for game state snapshots."""

    id: Optional[int] = None
    game_id: int
    round_id: int
    timestamp: datetime = Field(default_factory=datetime.now)
    game_state: Dict = Field(..., description="Complete game state")

    class Config:
        from_attributes = True


class GameDTO(BaseModel):
    """Data Transfer Object for complete game information.

    Represents the full state of a poker game, including:
    - Game configuration (blinds, ante, max players)
    - Game progress (rounds, current state)
    - Player participation and interactions
    - Historical data (chat, snapshots)

    This is the primary DTO for game state management and history tracking.
    """

    id: Optional[int] = None
    session_id: Optional[str] = None
    small_blind: int = Field(default=10)
    big_blind: int = Field(default=20)
    ante: int = Field(default=0)
    pot: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    duration: Optional[int] = None
    total_hands: int = Field(default=0)
    max_players: int = Field(default=6)
    game_type: str = Field(default="5-card-draw")
    winner_id: Optional[int] = None
    final_pot: int = Field(default=0)

    # Relationships
    rounds: List[RoundDTO] = Field(default_factory=list)
    players: List[GamePlayerAssociationDTO] = Field(default_factory=list)
    chat_messages: List[ChatMessageDTO] = Field(default_factory=list)
    snapshots: List[GameSnapshotDTO] = Field(default_factory=list)

    class Config:
        from_attributes = True


# Request/Response DTOs for specific operations


class CreateGameRequest(BaseModel):
    """Request DTO for initializing a new poker game.

    Contains all necessary parameters to configure and start a new game session,
    including blind sizes, player limits, and game variant selection.
    """

    small_blind: int = Field(default=10)
    big_blind: int = Field(default=20)
    ante: int = Field(default=0)
    max_players: int = Field(default=6)
    game_type: str = Field(default="5-card-draw")


class CreatePlayerRequest(BaseModel):
    """DTO for player creation request."""

    name: str = Field(..., description="Player's display name")


class GameActionRequest(BaseModel):
    """DTO for game actions."""

    action_type: str = Field(..., description="Type of action")
    amount: Optional[int] = Field(default=0, description="Amount for bets/raises")
    player_id: int = Field(..., description="ID of player taking action")


class GameStateResponse(BaseModel):
    """Response DTO for current game state information.

    Provides a comprehensive view of the current game state, including:
    - Active game details
    - Current round information
    - Player positions and states
    - Pot and betting information
    - Most recent action
    """

    game: GameDTO
    current_round: Optional[RoundDTO] = None
    active_players: List[GamePlayerAssociationDTO] = Field(default_factory=list)
    current_pot: int = Field(default=0)
    current_bet: int = Field(default=0)
    last_action: Optional[RoundActionDTO] = None

    class Config:
        from_attributes = True


class PlayerStatsResponse(BaseModel):
    """DTO for player statistics response."""

    player: PlayerDTO
    stats: PlayerStatsDTO
    recent_games: List[GameDTO] = Field(default_factory=list)

    class Config:
        from_attributes = True
