from collections.abc import Generator

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


def _make_engine():
    url = get_settings().database_url
    if url.startswith("sqlite"):
        # Tests run against in-memory SQLite. StaticPool keeps a single
        # connection so every session sees the same database.
        return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    # pool_pre_ping matters with Supabase's pooler, which drops idle
    # connections, and a free-tier instance is idle most of the time.
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5, pool_recycle=300)


engine = _make_engine()


def init_db() -> None:
    """Creates tables directly. Only used by tests, everything else runs Alembic migrations."""
    from app.db import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
