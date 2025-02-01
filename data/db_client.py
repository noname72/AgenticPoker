from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseClient:
    """Client for handling database operations."""

    _instance: Optional["DatabaseClient"] = None

    def __new__(
        cls, connection_string: str = "sqlite:///poker_game.db"
    ) -> "DatabaseClient":
        """Implement singleton pattern to ensure only one database client exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, connection_string: str = "sqlite:///poker_game.db") -> None:
        """Initialize database client.

        Args:
            connection_string (str): Database connection string
        """
        if not self._initialized:
            self.engine = create_engine(connection_string)
            self.SessionFactory = sessionmaker(bind=self.engine)
            self._session: Optional[Session] = None
            self._initialized = True

    @property
    def session(self) -> Session:
        """Get or create the shared database session.

        Returns:
            Session: The shared database session
        """
        if self._session is None:
            self._session = self.SessionFactory()
        return self._session

    def close(self) -> None:
        """Close the database session."""
        if self._session is not None:
            self._session.close()
            self._session = None

    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """Create a transaction context.

        Yields:
            Session: Database session with transaction
        """
        try:
            yield self.session
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def save_game_snapshot(
        self, game_id: int, round_id: int, game_state: Dict[str, Any]
    ) -> None:
        """Save a game snapshot to the database.

        Args:
            game_id (int): The ID of the game
            round_id (int): The ID of the round
            game_state (Dict[str, Any]): The game state to save
        """
        from data.model import GameSnapshot

        with self.transaction() as session:
            snapshot = GameSnapshot(
                game_id=game_id, round_id=round_id, game_state=game_state
            )
            session.add(snapshot)

    def save_player_snapshot(
        self,
        game_id: int,
        round_id: int,
        player_name: str,
        player_state: Dict[str, Any],
    ) -> None:
        """Save a player state snapshot to the database.

        Args:
            game_id (int): The ID of the game
            round_id (int): The ID of the round
            player_name (str): The name of the player
            player_state (Dict[str, Any]): The player state to save
        """
        from data.model import PlayerSnapshot

        with self.transaction() as session:
            snapshot = PlayerSnapshot(
                game_id=game_id,
                round_id=round_id,
                player_name=player_name,
                player_state=player_state,
            )
            session.add(snapshot)
