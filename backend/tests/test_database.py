import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic import command
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database import (
    DEFAULT_DB_PATH,
    PROJECT_ROOT,
    check_database_schema,
    create_db_engine,
    get_database_path,
    migrate_database,
    migration_config,
)
from backend.app.db_models import ListingRecord
from backend.app.main import create_app
from backend.app.repository import read_listings
from backend.app.seed import seed_listings


def test_migrations_match_orm_schema_and_can_be_repeated(engine):
    migrate_database(engine)
    check_database_schema(engine)
    assert inspect(engine).get_pk_constraint("listings")["constrained_columns"] == ["source", "id"]
    config = migration_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.check(config)


def test_migration_downgrade_and_upgrade_on_disposable_database(engine):
    config = migration_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
    assert not inspect(engine).has_table("listings")
    migrate_database(engine)
    check_database_schema(engine)
    assert inspect(engine).has_table("listings")


def test_seed_round_trips_every_field_and_is_repeatable(engine, listings):
    assert seed_listings(engine) == 12
    assert seed_listings(engine) == 0
    with Session(engine) as session:
        actual = {(record.source, record.id): record for record in read_listings(session)}
    expected = {(record.source, record.id): record for record in listings}
    assert actual == expected


def test_seed_preserves_edits_and_only_inserts_missing_identities(engine):
    seed_listings(engine)
    with Session(engine) as session, session.begin():
        session.get(ListingRecord, ("MLS_A", "A1")).price = 123456
        session.delete(session.get(ListingRecord, ("MLS_A", "A2")))
    assert seed_listings(engine) == 1
    with Session(engine) as session:
        assert session.get(ListingRecord, ("MLS_A", "A1")).price == 123456
        assert session.scalar(select(func.count()).select_from(ListingRecord)) == 12


@pytest.mark.parametrize("invalid", ["negative_price", "duplicate_identity"])
def test_invalid_seed_is_rejected_without_partial_inserts(engine, listings, tmp_path, invalid):
    first = listings[0].model_dump(mode="json")
    second = first if invalid == "duplicate_identity" else {**first, "id": "bad", "price": -1}
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps([first, second]))
    with pytest.raises((ValueError, ValidationError)):
        seed_listings(engine, path)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(ListingRecord)) == 0


def test_empty_seed_is_a_no_op(engine, tmp_path):
    path = tmp_path / "empty.json"
    path.write_text("[]")
    assert seed_listings(engine, path) == 0


def test_database_allows_same_id_in_different_sources_but_rejects_duplicate_pairs(engine, listings):
    values = listings[0].model_dump()
    with Session(engine) as session, session.begin():
        session.add_all([ListingRecord(**values), ListingRecord(**{**values, "source": "MLS_B"})])
    with Session(engine) as session, session.begin():
        with pytest.raises(IntegrityError):
            session.add(ListingRecord(**values))
            session.flush()


@pytest.mark.parametrize("invalid", [
    {"price": -1}, {"bedrooms": -1}, {"bedrooms": 1.5}, {"bathrooms": -1},
    {"sqft": -1}, {"sqft": 1.5}, {"latitude": 91}, {"longitude": -181},
    {"status": "unknown"}, {"source": ""}, {"id": ""}, {"address": ""},
    {"description": None},
])
def test_database_enforces_record_constraints(engine, listings, invalid):
    values = {**listings[0].model_dump(), **invalid}
    with Session(engine) as session:
        with pytest.raises(IntegrityError):
            session.add(ListingRecord(**values))
            session.commit()


def test_api_reads_updates_inserts_and_deletes_without_restart(client, engine, listings):
    assert client.get("/api/listings").json()["total"] == 12
    with Session(engine) as session, session.begin():
        record = session.get(ListingRecord, ("MLS_A", "A1"))
        record.price = 123456
        record.city = "Updated city"
    updated = client.get("/api/listings", params={"city": "Updated city"}).json()
    assert updated["total"] == 1
    assert updated["items"][0]["price"] == 123456

    with Session(engine) as session, session.begin():
        session.add(ListingRecord(**{**listings[0].model_dump(), "id": "new"}))
    assert client.get("/api/listings").json()["total"] == 13
    with Session(engine) as session, session.begin():
        session.delete(session.get(ListingRecord, ("MLS_A", "new")))
    assert client.get("/api/listings").json()["total"] == 12


def test_edits_and_deletions_survive_app_restart_without_reseeding(engine):
    seed_listings(engine)
    path = Path(engine.url.database)
    with TestClient(create_app(path)) as client:
        assert client.get("/api/listings").json()["total"] == 12
    with Session(engine) as session, session.begin():
        record = session.get(ListingRecord, ("MLS_A", "A1"))
        record.price = 111111
        record.city = "Persistent city"
        session.delete(session.get(ListingRecord, ("MLS_A", "A2")))
    with TestClient(create_app(path)) as restarted:
        assert restarted.get("/api/listings").json()["total"] == 11
        result = restarted.get("/api/listings", params={"city": "Persistent city"}).json()
        assert result["items"][0]["price"] == 111111


def test_migrated_empty_database_is_valid_and_not_automatically_seeded(engine):
    with TestClient(create_app(Path(engine.url.database))) as client:
        response = client.get("/api/listings")
        assert response.status_code == 200
        assert response.json()["total"] == 0


def test_startup_without_migrations_has_actionable_error(tmp_path):
    with pytest.raises(RuntimeError, match="alembic upgrade head"):
        with TestClient(create_app(tmp_path / "unmigrated.sqlite3")):
            pass


def test_database_failure_returns_clear_503(client, engine):
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE listings")
    response = client.get("/api/listings")
    assert response.status_code == 503
    assert response.json() == {"detail": "Listing database unavailable. Please try again."}


def test_database_path_configuration(monkeypatch, tmp_path):
    monkeypatch.delenv("LISTINGS_DB_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    assert get_database_path() == DEFAULT_DB_PATH
    monkeypatch.setenv("LISTINGS_DB_PATH", str(tmp_path / "custom.sqlite3"))
    assert get_database_path() == tmp_path / "custom.sqlite3"


def test_migration_and_seed_commands_persist_across_processes(tmp_path):
    path = tmp_path / "cli.sqlite3"
    env = {**os.environ, "LISTINGS_DB_PATH": str(path)}
    for module, args in [("alembic", ["upgrade", "head"]), ("backend.app.seed", [])]:
        subprocess.run([sys.executable, "-m", module, *args], cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, check=True)
    second_seed = subprocess.run([sys.executable, "-m", "backend.app.seed"], cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, check=True)
    assert "Inserted 0 listing(s)" in second_seed.stdout
    engine = create_db_engine(path)
    try:
        check_database_schema(engine)
        with Session(engine) as session:
            assert len(read_listings(session)) == 12
    finally:
        engine.dispose()
