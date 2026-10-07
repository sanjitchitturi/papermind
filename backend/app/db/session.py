from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()

# echo=False on purpose, the SQL logs get noisy fast once ingestion is running
engine = create_engine(settings.database_url, echo=False)


def init_db() -> None:
    # In a real production app this would be Alembic migrations. For a
    # portfolio project we create tables directly on startup, it is simpler
    # and there is no production data to protect from a bad migration.
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
