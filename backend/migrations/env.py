from alembic import context

from backend.app.database import create_db_engine, get_database_path
from backend.app.db_models import ListingRecord
from sqlalchemy import URL

target_metadata = ListingRecord.metadata


def run_with_connection(connection):
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=URL.create("sqlite+pysqlite", database=str(get_database_path())),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    connection = context.config.attributes.get("connection")
    if connection is not None:
        run_with_connection(connection)
    else:
        engine = create_db_engine()
        try:
            with engine.connect() as connection:
                run_with_connection(connection)
        finally:
            engine.dispose()
