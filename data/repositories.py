from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from data.model import (
    ChatMessage,
    Game,
    GameSnapshot,
    Player,
    PlayerStats,
    Round,
    RoundAction,
)


class BaseRepository:
    """Base repository with common CRUD operations.

    Provides basic database transaction management functionality for all repository classes.

    Args:
        session (Session): SQLAlchemy database session
    """

    def __init__(self, session: Session):
        self.session = session

    def commit(self) -> None:
        """Commit the current transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self.session.rollback()


class GameRepository(BaseRepository):
    """Repository for Game-related database operations.

    Handles creation, retrieval, and updates of poker game records in the database.
    """

    def create(
        self,
        small_blind: int,
        big_blind: int,
        ante: int = 0,
        max_players: int = 6,
        game_type: str = "5-card-draw",
    ) -> Game:
        """Create a new poker game.

        Args:
            small_blind (int): Small blind amount
            big_blind (int): Big blind amount
            ante (int, optional): Ante amount. Defaults to 0.
            max_players (int, optional): Maximum number of players. Defaults to 6.
            game_type (str, optional): Type of poker game. Defaults to "5-card-draw".

        Returns:
            Game: Newly created game instance
        """
        game = Game(
            small_blind=small_blind,
            big_blind=big_blind,
            ante=ante,
            max_players=max_players,
            game_type=game_type,
        )
        self.session.add(game)
        self.session.commit()
        return game

    def get_by_id(self, game_id: int) -> Optional[Game]:
        """Retrieve a game by ID."""
        return self.session.query(Game).filter(Game.id == game_id).first()

    def get_active_games(self) -> List[Game]:
        """Get all active games (where winner_id is None)."""
        return self.session.query(Game).filter(Game.winner_id.is_(None)).all()

    def update(self, game_id: int, **kwargs) -> Optional[Game]:
        """Update game attributes."""
        game = self.get_by_id(game_id)
        if game:
            for key, value in kwargs.items():
                setattr(game, key, value)
            self.session.commit()
        return game

    def end_game(self, game_id: int, winner_id: int, final_pot: int) -> Optional[Game]:
        """End a game by setting winner and final pot.

        Args:
            game_id (int): ID of the game to end
            winner_id (int): ID of the winning player
            final_pot (int): Final pot amount

        Returns:
            Optional[Game]: Updated game instance or None if game not found

        Note:
            Also calculates and stores the game duration in seconds
        """
        game = self.get_by_id(game_id)
        if game:
            game.winner_id = winner_id
            game.final_pot = final_pot
            game.duration = int((datetime.utcnow() - game.created_at).total_seconds())
            self.session.commit()
        return game


class PlayerRepository(BaseRepository):
    """Repository for Player-related database operations.

    Handles player creation, retrieval, and statistics updates.
    """

    def create(self, name: str) -> Player:
        """Create a new player."""
        player = Player(name=name)
        self.session.add(player)
        self.session.commit()
        return player

    def get_by_id(self, player_id: int) -> Optional[Player]:
        """Retrieve a player by ID."""
        return self.session.query(Player).filter(Player.id == player_id).first()

    def get_by_name(self, name: str) -> Optional[Player]:
        """Retrieve a player by name."""
        return self.session.query(Player).filter(Player.name == name).first()

    def get_all(self) -> List[Player]:
        """Get all players."""
        return self.session.query(Player).all()

    def update_stats(
        self, player_id: int, game_stats: Dict[str, Any]
    ) -> Optional[PlayerStats]:
        """Update player statistics after a game.

        Args:
            player_id (int): ID of the player to update
            game_stats (Dict[str, Any]): Dictionary containing game statistics with keys:
                - won (bool): Whether the player won the game
                - winnings (int): Amount won in this game
                - pot_size (int): Size of the largest pot
                - duration (int): Game duration in seconds

        Returns:
            Optional[PlayerStats]: Updated player stats or None if player not found
        """
        player = self.get_by_id(player_id)
        if not player or not player.stats:
            return None

        stats = player.stats
        stats.games_played += 1
        if game_stats.get("won", False):
            stats.hands_won += 1
        stats.total_winnings += game_stats.get("winnings", 0)
        stats.largest_pot = max(stats.largest_pot, game_stats.get("pot_size", 0))
        stats.total_time_played += game_stats.get("duration", 0)

        self.session.commit()
        return stats


class RoundRepository(BaseRepository):
    """Repository for Round-related database operations.

    Handles creation, retrieval, and management of poker game rounds, including
    tracking round outcomes and side pots.
    """

    def create(self, game_id: int, round_number: int) -> Round:
        """Create a new poker game round.

        Args:
            game_id (int): ID of the game this round belongs to
            round_number (int): Sequential number of this round within the game

        Returns:
            Round: Newly created round instance
        """
        round = Round(game_id=game_id, round_number=round_number)
        self.session.add(round)
        self.session.commit()
        return round

    def get_by_id(self, round_id: int) -> Optional[Round]:
        """Retrieve a round by its ID.

        Args:
            round_id (int): Unique identifier of the round

        Returns:
            Optional[Round]: Round instance if found, None otherwise
        """
        return self.session.query(Round).filter(Round.id == round_id).first()

    def get_game_rounds(self, game_id: int) -> List[Round]:
        """Get all rounds for a specific game in chronological order.

        Args:
            game_id (int): ID of the game to get rounds for

        Returns:
            List[Round]: List of rounds associated with the game
        """
        return self.session.query(Round).filter(Round.game_id == game_id).all()

    def end_round(
        self, round_id: int, winning_hand: str, side_pots: Optional[Dict] = None
    ) -> Optional[Round]:
        """End a round and record the winning hand and side pots.

        Args:
            round_id (int): ID of the round to end
            winning_hand (str): Description of the winning poker hand
            side_pots (Optional[Dict]): Dictionary containing side pot information
                where keys are player IDs and values are pot amounts

        Returns:
            Optional[Round]: Updated round instance or None if round not found

        Note:
            Sets the ended_at timestamp automatically to current UTC time
        """
        round = self.get_by_id(round_id)
        if round:
            round.ended_at = datetime.utcnow()
            round.winning_hand = winning_hand
            if side_pots:
                round.side_pots = side_pots
            self.session.commit()
        return round


class RoundActionRepository(BaseRepository):
    """Repository for RoundAction-related database operations.

    Manages player actions during poker rounds, including bets, folds, and other
    gameplay decisions. Also tracks AI decision-making metrics when applicable.
    """

    def create(
        self,
        round_id: int,
        association_id: int,
        action_type: str,
        amount: int = 0,
        confidence_score: Optional[float] = None,
        decision_factors: Optional[Dict] = None,
    ) -> RoundAction:
        """Create a new player action within a round.

        Args:
            round_id (int): ID of the round this action belongs to
            association_id (int): ID of the player making the action
            action_type (str): Type of poker action (e.g., 'bet', 'fold', 'call')
            amount (int, optional): Amount of chips involved in the action. Defaults to 0.
            confidence_score (Optional[float]): AI confidence score if applicable
            decision_factors (Optional[Dict]): Dictionary containing AI decision factors
                and their weights in making this action

        Returns:
            RoundAction: Newly created action instance

        Note:
            Timestamp is automatically set to current UTC time when created
        """
        action = RoundAction(
            round_id=round_id,
            association_id=association_id,
            action_type=action_type,
            amount=amount,
            confidence_score=confidence_score,
            decision_factors=decision_factors,
        )
        self.session.add(action)
        self.session.commit()
        return action

    def get_round_actions(self, round_id: int) -> List[RoundAction]:
        """Get all actions for a specific round in chronological order.

        Args:
            round_id (int): ID of the round to get actions for

        Returns:
            List[RoundAction]: Ordered list of actions taken during the round
        """
        return (
            self.session.query(RoundAction)
            .filter(RoundAction.round_id == round_id)
            .order_by(RoundAction.timestamp)
            .all()
        )


class ChatMessageRepository(BaseRepository):
    """Repository for ChatMessage-related database operations.

    Handles creation and retrieval of in-game chat messages between players.
    Maintains a chronological record of game communication.
    """

    def create(self, game_id: int, player_id: int, message: str) -> ChatMessage:
        """Create a new chat message.

        Args:
            game_id (int): ID of the game this message belongs to
            player_id (int): ID of the player sending the message
            message (str): Content of the chat message

        Returns:
            ChatMessage: Newly created chat message instance

        Note:
            Timestamp is automatically set to current UTC time when created
        """
        chat_message = ChatMessage(
            game_id=game_id,
            player_id=player_id,
            message=message,
        )
        self.session.add(chat_message)
        self.session.commit()
        return chat_message

    def get_game_messages(self, game_id: int) -> List[ChatMessage]:
        """Get all chat messages for a specific game.

        Args:
            game_id (int): ID of the game to retrieve messages for

        Returns:
            List[ChatMessage]: Chronologically ordered list of chat messages for the game
        """
        return (
            self.session.query(ChatMessage)
            .filter(ChatMessage.game_id == game_id)
            .order_by(ChatMessage.timestamp)
            .all()
        )


class GameSnapshotRepository(BaseRepository):
    """Repository for GameSnapshot-related database operations.

    Manages game state snapshots that capture the complete state of the game at specific
    points in time. Useful for game replay, analysis, and state recovery.
    """

    def create(self, game_id: int, round_id: int, game_state: Dict) -> GameSnapshot:
        """Create a new game snapshot.

        Args:
            game_id (int): ID of the game this snapshot belongs to
            round_id (int): ID of the round when this snapshot was taken
            game_state (Dict): Dictionary containing complete game state information,
                including player hands, pot amounts, and current board state

        Returns:
            GameSnapshot: Newly created snapshot instance

        Note:
            Timestamp is automatically set to current UTC time when created
        """
        snapshot = GameSnapshot(
            game_id=game_id,
            round_id=round_id,
            game_state=game_state,
        )
        self.session.add(snapshot)
        self.session.commit()
        return snapshot

    def get_game_snapshots(self, game_id: int) -> List[GameSnapshot]:
        """Get all snapshots for a specific game.

        Args:
            game_id (int): ID of the game to retrieve snapshots for

        Returns:
            List[GameSnapshot]: Chronologically ordered list of game snapshots
        """
        return (
            self.session.query(GameSnapshot)
            .filter(GameSnapshot.game_id == game_id)
            .order_by(GameSnapshot.timestamp)
            .all()
        )

    def get_round_snapshot(self, round_id: int) -> Optional[GameSnapshot]:
        """Get the snapshot for a specific round.

        Args:
            round_id (int): ID of the round to retrieve the snapshot for

        Returns:
            Optional[GameSnapshot]: Snapshot instance if found, None otherwise

        Note:
            Returns the most recent snapshot if multiple exist for the same round
        """
        return (
            self.session.query(GameSnapshot)
            .filter(GameSnapshot.round_id == round_id)
            .first()
        )
