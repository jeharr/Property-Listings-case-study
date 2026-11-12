from sqlalchemy import select
from sqlalchemy.orm import Session

from .db_models import ListingRecord
from .models import Listing


def read_listings(session: Session) -> tuple[Listing, ...]:
    """Read current records for each search, without retaining an application cache."""
    records = session.scalars(select(ListingRecord)).all()
    return tuple(Listing.model_validate(record, from_attributes=True) for record in records)
