import json

import pytest
from pydantic import ValidationError
from sqlalchemy import delete, inspect, select
from sqlalchemy.orm import Session

from backend.app import initialize
from backend.app.database import create_db_engine
from backend.app.db_models import ListingRecord
from backend.app.initialize import initialize_database
from backend.app.seed import seed_listings


def test_first_initialization_migrates_and_seeds(tmp_path):
    engine = create_db_engine(tmp_path / "new.sqlite3")
    try:
        assert initialize_database(engine) == 12
        with Session(engine) as session:
            assert len(session.scalars(select(ListingRecord)).all()) == 12
    finally:
        engine.dispose()


def test_repeat_initialization_preserves_edits_and_deletions(engine):
    seed_listings(engine)
    with Session(engine) as session, session.begin():
        session.get(ListingRecord, ("MLS_A", "A1")).price = 123456
        session.delete(session.get(ListingRecord, ("MLS_A", "A2")))
    assert initialize_database(engine) is None
    with Session(engine) as session:
        assert session.get(ListingRecord, ("MLS_A", "A1")).price == 123456
        assert session.get(ListingRecord, ("MLS_A", "A2")) is None


def test_initialized_empty_database_is_not_reseeded(engine):
    seed_listings(engine)
    with Session(engine) as session, session.begin():
        session.execute(delete(ListingRecord))
    assert initialize_database(engine) is None
    with Session(engine) as session:
        assert session.scalars(select(ListingRecord)).all() == []


def test_bad_fixture_is_rejected_before_schema_creation(tmp_path, monkeypatch):
    fixture = tmp_path / "invalid.json"
    fixture.write_text(json.dumps([{"id": "invalid"}]))
    monkeypatch.setattr(initialize, "DATA_PATH", fixture)
    engine = create_db_engine(tmp_path / "new.sqlite3")
    try:
        with pytest.raises(ValidationError):
            initialize_database(engine)
        assert not inspect(engine).has_table("listings")
    finally:
        engine.dispose()
