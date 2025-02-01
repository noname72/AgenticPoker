from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Game(Base):
    """
    Represents a single poker game instance.

    Tracks the state and settings of a poker game, including blinds, antes, pot amounts,
    and game progression. Also maintains relationships with players, rounds, and game history.

    Attributes:
        id (int): Unique identifier for the game
        session_id (str): External reference ID for logging
        small_blind (int): Small blind amount, defaults to 10
        big_blind (int): Big blind amount, defaults to 20
        ante (int): Ante amount, defaults to 0
        pot (int): Current pot amount
        duration (int): Game duration in seconds
        total_hands (int): Number of hands played
        max_players (int): Maximum allowed players, defaults to 6
        game_type (str): Variant of poker being played
    """

    __tablename__ = "games"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=True)  # For logging or external reference
    small_blind = Column(Integer, default=10)
    big_blind = Column(Integer, default=20)
    ante = Column(Integer, default=0)
    pot = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Add game session metadata
    duration = Column(Integer, nullable=True)  # Duration in seconds
    total_hands = Column(Integer, default=0)
    max_players = Column(Integer, default=6)
    game_type = Column(String, default="5-card-draw")  # For future variants

    # Add game outcome tracking
    winner_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    final_pot = Column(Integer, default=0)

    # Relationship to rounds
    rounds = relationship("Round", back_populates="game")

    # Relationship to the many-to-many table associating games and players
    players_association = relationship("GamePlayerAssociation", back_populates="game")

    # Add new relationships
    chat_messages = relationship("ChatMessage", back_populates="game")
    game_snapshots = relationship("GameSnapshot", back_populates="game")

    def __repr__(self):
        return f"<Game(id={self.id}, session_id={self.session_id})>"


class Player(Base):
    """
    Represents a player in the poker system.

    Maintains player identity and relationships to games they participate in.
    Links to player statistics and game-specific state through associations.

    Attributes:
        id (int): Unique identifier for the player
        name (str): Unique username of the player
        created_at (datetime): Timestamp of player creation
        stats (PlayerStats): One-to-one relationship with player statistics
    """

    __tablename__ = "players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to the many-to-many table associating games and players
    games_association = relationship("GamePlayerAssociation", back_populates="player")

    # Add relationship to Player class
    stats = relationship("PlayerStats", uselist=False, back_populates="player")

    def __repr__(self):
        return f"<Player(id={self.id}, name='{self.name}')>"


class GamePlayerAssociation(Base):
    """
    Associates players with specific games and tracks their game state.

    Represents the many-to-many relationship between games and players while
    maintaining game-specific player state such as chip count and current actions.

    Attributes:
        game_id (int): Foreign key to the associated game
        player_id (int): Foreign key to the associated player
        chips (int): Player's current chip count in this game
        folded (bool): Whether the player has folded in the current hand
        bet (int): Player's current bet amount
        current_hand (str): Serialized representation of player's cards
    """

    __tablename__ = "game_player_associations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    chips = Column(Integer, default=1000)
    folded = Column(Boolean, default=False)
    bet = Column(Integer, default=0)

    # Relationships
    game = relationship("Game", back_populates="players_association")
    player = relationship("Player", back_populates="games_association")

    # Example of storing a JSON-serialized or text-serialized representation of a hand
    current_hand = Column(Text, nullable=True)

    def __repr__(self):
        return (
            f"<GamePlayerAssociation("
            f"game_id={self.game_id}, player_id={self.player_id}, chips={self.chips})>"
        )


class Round(Base):
    """
    Represents a single round of betting (or a phase in 5-card-draw) within a game.

    Tracks the progression of a single betting round, including pot size, community cards,
    and player actions. Maintains historical data for game replay and analysis.

    Attributes:
        id (int): Unique identifier for the round
        game_id (int): Foreign key to the associated game
        round_number (int): Sequential number of this round within the game
        pot (int): Current pot amount for this round
        started_at (datetime): Timestamp when round began
        ended_at (datetime): Timestamp when round ended, nullable
        community_cards (str): Serialized community cards for Hold'em variants
        winning_hand (str): Serialized representation of the winning hand
        side_pots (dict): JSON structure tracking side pot amounts and eligible players
    """

    __tablename__ = "rounds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    round_number = Column(Integer, default=1)
    pot = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    # Add hand history tracking
    community_cards = Column(Text, nullable=True)  # For future Hold'em support
    winning_hand = Column(Text, nullable=True)  # Store the winning hand

    # Add side pot tracking
    side_pots = Column(
        JSON, nullable=True
    )  # Store side pot amounts and eligible players

    # Relationship back to the game
    game = relationship("Game", back_populates="rounds")

    # Relationship to logging of player actions in this round
    actions = relationship("RoundAction", back_populates="round")

    def __repr__(self):
        return f"<Round(id={self.id}, game_id={self.game_id}, round_number={self.round_number})>"


class RoundAction(Base):
    """
    Logs any player action in a specific round (bet, call, fold, raise).

    Records detailed information about each player action, including AI decision metrics
    when applicable. Provides comprehensive tracking for game analysis and replay.

    Attributes:
        id (int): Unique identifier for the action
        round_id (int): Foreign key to the associated round
        association_id (int): Foreign key to game_player_associations
        action_type (str): Type of action taken (fold, call, raise, etc.)
        amount (int): Chip amount involved in the action
        timestamp (datetime): When the action occurred
        confidence_score (float): AI confidence in decision, nullable
        decision_factors (dict): JSON structure detailing AI reasoning
        processing_time (float): Time taken for AI decision in milliseconds
    """

    __tablename__ = "round_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    round_id = Column(Integer, ForeignKey("rounds.id"), nullable=False)
    association_id = Column(
        Integer, ForeignKey("game_player_associations.id"), nullable=False
    )
    action_type = Column(String)  # e.g. 'fold', 'call', 'raise'
    amount = Column(Integer, default=0)  # amount of chips for bets or raises
    timestamp = Column(DateTime, default=datetime.utcnow)

    round = relationship("Round", back_populates="actions")

    # It's often helpful to link directly to the GamePlayerAssociation
    # to see which player's action this was.
    player_association = relationship("GamePlayerAssociation")

    # Add AI decision tracking
    confidence_score = Column(Float, nullable=True)
    decision_factors = Column(JSON, nullable=True)  # Store AI reasoning
    processing_time = Column(Float, nullable=True)  # Time taken for decision in ms

    def __repr__(self):
        return (
            f"<RoundAction("
            f"round_id={self.round_id}, association_id={self.association_id}, "
            f"action_type='{self.action_type}', amount={self.amount})>"
        )


class ChatMessage(Base):
    """
    Stores in-game chat messages.

    Maintains a record of player communication during games, providing context
    for game interactions and player behavior analysis.

    Attributes:
        id (int): Unique identifier for the message
        game_id (int): Foreign key to the associated game
        player_id (int): Foreign key to the message sender
        message (str): Content of the chat message
        timestamp (datetime): When the message was sent
    """

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    game = relationship("Game", back_populates="chat_messages")
    player = relationship("Player")


class GameSnapshot(Base):
    """
    Stores game state snapshots for replay/debugging.

    Captures complete game state at specific points in time, enabling
    game replay, debugging, and detailed analysis of game progression.

    Attributes:
        id (int): Unique identifier for the snapshot
        game_id (int): Foreign key to the associated game
        round_id (int): Foreign key to the current round
        timestamp (datetime): When the snapshot was taken
        game_state (dict): JSON structure containing complete game state
    """

    __tablename__ = "game_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    round_id = Column(Integer, ForeignKey("rounds.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Store complete game state as JSON
    game_state = Column(JSON, nullable=False)

    # Relationships
    game = relationship("Game", back_populates="game_snapshots")
    round = relationship("Round")


class PlayerStats(Base):
    """
    Tracks comprehensive statistics for a player across all their games.

    Maintains both basic and advanced metrics to analyze player performance
    and playing style over time.

    Attributes:
        player_id (int): Foreign key to the associated player
        games_played (int): Total number of games participated in
        hands_won (int): Total number of hands won
        total_winnings (int): Cumulative chip winnings
        largest_pot (int): Largest single pot won
        total_time_played (int): Total time spent playing in seconds
        bluff_success_rate (float): Percentage of successful bluffs
        avg_bet_size (float): Average betting amount
    """

    __tablename__ = "player_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)

    # Lifetime stats
    games_played = Column(Integer, default=0)
    hands_won = Column(Integer, default=0)
    total_winnings = Column(Integer, default=0)
    largest_pot = Column(Integer, default=0)
    total_time_played = Column(Integer, default=0)  # In seconds

    # Advanced stats
    bluff_success_rate = Column(Float, default=0.0)
    avg_bet_size = Column(Float, default=0.0)

    # Relationship
    player = relationship("Player", back_populates="stats")


class PlayerSnapshot(Base):
    """Model for storing player state snapshots."""

    __tablename__ = "player_snapshots"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, nullable=False)
    round_id = Column(Integer, nullable=False)
    player_name = Column(String, nullable=False)
    player_state = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
