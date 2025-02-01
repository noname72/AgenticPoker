from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from data.model import Base, Game


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
            # Create all tables
            Base.metadata.create_all(self.engine)
            self.SessionFactory = sessionmaker(bind=self.engine)
            self._session: Optional[Session] = None
            self._current_game: Optional[Game] = None
            self._initialized = True

    @property
    def session(self) -> Session:
        """Get or create the shared database session."""
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
        """Create a transaction context."""
        try:
            yield self.session
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    def _ensure_game_exists(self, session_id: str) -> Game:
        """Ensure a game record exists for the given session."""
        if not self._current_game:
            with self.transaction() as session:
                self._current_game = Game(session_id=session_id)
                session.add(self._current_game)
        return self._current_game

    def save_round_snapshot(
        self, session_id: str, round_id: int, round_state: Dict[str, Any]
    ) -> None:
        """Save a round snapshot to the database."""
        from data.model import RoundSnapshot

        with self.transaction() as session:
            game = self._ensure_game_exists(session_id)
            snapshot = RoundSnapshot(
                game_id=game.id,
                round_id=round_id,
                round_state=(
                    round_state.to_dict()
                    if hasattr(round_state, "to_dict")
                    else round_state
                ),
            )
            session.add(snapshot)

    def save_game_snapshot(
        self, session_id: str, round_id: int, game_state: Dict[str, Any]
    ) -> None:
        """Save a game snapshot to the database."""
        from data.model import GameSnapshot

        with self.transaction() as session:
            game = self._ensure_game_exists(session_id)
            snapshot = GameSnapshot(
                game_id=game.id, round_id=round_id, game_state=game_state.to_dict()
            )
            session.add(snapshot)

    def save_player_snapshot(
        self,
        session_id: str,
        round_id: int,
        player_name: str,
        player_state: Dict[str, Any],
    ) -> None:
        """Save a player state snapshot to the database."""
        from data.model import PlayerSnapshot

        with self.transaction() as session:
            game = self._ensure_game_exists(session_id)
            snapshot = PlayerSnapshot(
                game_id=game.id,
                round_id=round_id,
                player_name=player_name,
                player_state=player_state,
            )
            session.add(snapshot)
