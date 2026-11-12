"""Explicit, repeatable sample import: insert missing identities, preserve existing rows."""

import argparse
from pathlib import Path

from pydantic import TypeAdapter
from sqlalchemy import Engine
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from .database import PROJECT_ROOT, check_database_schema, create_db_engine
from .db_models import ListingRecord
from .models import Listing

DATA_PATH = PROJECT_ROOT / "data" / "sample_listings.json"


def load_listings(path: Path) -> tuple[Listing, ...]:
    listings = TypeAdapter(list[Listing]).validate_json(path.read_text(encoding="utf-8"))
    identities = [(listing.source, listing.id) for listing in listings]
    if len(identities) != len(set(identities)):
        raise ValueError("Dataset contains duplicate (source, id) identities.")
    return tuple(listings)


def seed_listings(engine: Engine, path: Path = DATA_PATH) -> int:
    # Validate the entire import before any writes; insert the batch in one transaction.
    listings = load_listings(path)
    check_database_schema(engine)
    if not listings:
        return 0
    statement = (
        insert(ListingRecord)
        .values([listing.model_dump() for listing in listings])
        .on_conflict_do_nothing(index_elements=[ListingRecord.source, ListingRecord.id])
    )
    with Session(engine) as session, session.begin():
        result = session.execute(statement)
        return result.rowcount


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=DATA_PATH, help="Listing JSON file to import")
    args = parser.parse_args()
    engine = create_db_engine()
    try:
        count = seed_listings(engine, args.file)
        print(f"Inserted {count} listing(s). Existing records were preserved.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
