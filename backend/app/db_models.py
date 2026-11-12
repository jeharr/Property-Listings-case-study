"""Persisted feed records, separate from API validation/response models."""

from datetime import date

from sqlalchemy import CheckConstraint, Date, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ListingRecord(Base):
    __tablename__ = "listings"
    __table_args__ = (
        CheckConstraint("length(source) > 0 AND length(id) > 0", name="ck_listings_identity"),
        CheckConstraint("length(address) > 0", name="ck_listings_address"),
        CheckConstraint("price >= 0", name="ck_listings_price"),
        CheckConstraint("bedrooms >= 0 AND bedrooms = CAST(bedrooms AS INTEGER)", name="ck_listings_bedrooms"),
        CheckConstraint("bathrooms >= 0", name="ck_listings_bathrooms"),
        CheckConstraint("sqft >= 0 AND sqft = CAST(sqft AS INTEGER)", name="ck_listings_sqft"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_listings_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_listings_longitude"),
        CheckConstraint("status IN ('active', 'pending', 'sold')", name="ck_listings_status"),
    )

    source: Mapped[str] = mapped_column(String, primary_key=True)
    id: Mapped[str] = mapped_column(String, primary_key=True)
    address: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String)
    state: Mapped[str] = mapped_column(String)
    zip: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(Float)
    bedrooms: Mapped[int] = mapped_column(Integer)
    bathrooms: Mapped[float] = mapped_column(Float)
    sqft: Mapped[int] = mapped_column(Integer)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    # Keep the API/feed attribute name while using a conventional SQL column name.
    listedDate: Mapped[date] = mapped_column("listed_date", Date)
    status: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
