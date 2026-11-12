import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import check_database_schema, create_db_engine, get_session
from .models import Listing, SearchFilters, SearchResponse
from .repository import read_listings
from .search import PageOutOfRange, search_listings

logger = logging.getLogger(__name__)
router = APIRouter()


def current_date() -> date:
    return datetime.now(UTC).date()


def get_listings(session: Annotated[Session, Depends(get_session)]) -> tuple[Listing, ...]:
    return read_listings(session)


@router.get("/api/listings", response_model=SearchResponse)
def listings(
    filters: Annotated[SearchFilters, Query()],
    data: Annotated[tuple[Listing, ...], Depends(get_listings)],
    today: Annotated[date, Depends(current_date)],
) -> SearchResponse:
    try:
        return search_listings(data, filters, as_of=today)
    except PageOutOfRange as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"loc": ["query", "page"], "msg": str(exc), "type": "value_error"}],
        ) from exc


def database_error(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("Listing database query failed", exc_info=exc)
    return JSONResponse(status_code=503, content={"detail": "Listing database unavailable. Please try again."})


def create_app(database_path: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        engine = create_db_engine(database_path)
        try:
            check_database_schema(engine)
            app.state.engine = engine
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="Property Listings Search", version="1.0.0", lifespan=lifespan)
    application.include_router(router)
    application.add_exception_handler(SQLAlchemyError, database_error)
    return application


app = create_app()
