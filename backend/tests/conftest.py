from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.database import create_db_engine, migrate_database
from backend.app.main import create_app, current_date
from backend.app.seed import DATA_PATH, load_listings, seed_listings


@pytest.fixture
def today():
    return date(2026, 11, 10)


@pytest.fixture
def listings():
    return load_listings(DATA_PATH)


@pytest.fixture
def engine(tmp_path):
    database = create_db_engine(tmp_path / "test.sqlite3")
    migrate_database(database)
    try:
        yield database
    finally:
        database.dispose()


@pytest.fixture
def client(engine, today):
    seed_listings(engine)
    app = create_app(database_path=Path(engine.url.database))
    app.dependency_overrides[current_date] = lambda: today
    with TestClient(app) as client:
        yield client
