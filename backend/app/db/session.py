"""A single SQLite database is the persistent source of truth."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


def _make_engine():
    url = get_settings().database_url
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite":
        raise ValueError("PaperMind uses SQLite. Set DATABASE_URL to a sqlite:/// path.")
    memory = parsed.database in (None, "", ":memory:")
    if not memory:
        Path(parsed.database).expanduser().parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        url, connect_args={"check_same_thread": False, "timeout": 30}, **({"poolclass": StaticPool} if memory else {})
    )

    @event.listens_for(engine, "connect")
    def configure_connection(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        if not memory:
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


engine = _make_engine()


def init_db() -> None:
    from app.db import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
