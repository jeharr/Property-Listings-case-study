"""SQLite configuration, migration checks, and request-scoped sessions."""

import os
from collections.abc import Iterator
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import Request
from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "listings.sqlite3"


class Base(DeclarativeBase):
    pass


def get_database_path() -> Path:
    configured = os.environ.get("LISTINGS_DB_PATH")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DB_PATH


def create_db_engine(path: Path | None = None) -> Engine:
    path = (path or get_database_path()).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        URL.create("sqlite+pysqlite", database=str(path)),
        # FastAPI may enter/exit a synchronous dependency on different threads.
        # Explicit transaction control also covers SQLite DDL and reads (Python 3.12+).
        connect_args={"check_same_thread": False, "autocommit": False},
    )


def migration_config() -> Config:
    return Config(str(PROJECT_ROOT / "alembic.ini"))


def migrate_database(engine: Engine) -> None:
    """Apply migrations explicitly; application startup never changes the schema."""
    config = migration_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def check_database_schema(engine: Engine) -> None:
    head = ScriptDirectory.from_config(migration_config()).get_current_head()
    with engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
    if current != head:
        raise RuntimeError(
            "Listing database schema is missing or out of date. From the project root, "
            "run `.venv/bin/python -m alembic upgrade head`, then "
            "`.venv/bin/python -m backend.app.seed` to load sample listings if needed."
        )


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session
