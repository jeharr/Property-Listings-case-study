"""Explicit launcher setup: migrate the database and seed only its first initialization."""

from sqlalchemy import Engine, inspect

from .database import create_db_engine, migrate_database
from .seed import DATA_PATH, load_listings, seed_listings


def initialize_database(engine: Engine) -> int | None:
    already_initialized = inspect(engine).has_table("listings")
    if not already_initialized:
        # Reject invalid fixture data before creating the schema.
        load_listings(DATA_PATH)
    migrate_database(engine)
    return None if already_initialized else seed_listings(engine)


def main() -> None:
    engine = create_db_engine()
    try:
        count = initialize_database(engine)
        if count is None:
            print("Database migrated. Existing listings preserved; no reseeding.")
        else:
            print(f"Database initialized with {count} sample listing(s).")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
