"""Run the browser-test API with its own disposable, migrated, seeded database."""

from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

from backend.app.database import create_db_engine, migrate_database
from backend.app.main import create_app
from backend.app.seed import seed_listings


def main() -> None:
    with TemporaryDirectory(prefix="brillio-e2e-") as directory:
        path = Path(directory) / "listings.sqlite3"
        engine = create_db_engine(path)
        try:
            migrate_database(engine)
            seed_listings(engine)
        finally:
            engine.dispose()
        uvicorn.run(create_app(path), host="127.0.0.1", port=8001)


if __name__ == "__main__":
    main()
