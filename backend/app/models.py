from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PAGE_SIZE = 3


class Listing(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    address: str = Field(min_length=1)
    city: str
    state: str
    zip: str
    price: float = Field(ge=0, allow_inf_nan=False)
    bedrooms: int = Field(ge=0)
    bathrooms: float = Field(ge=0, allow_inf_nan=False)
    sqft: int = Field(ge=0)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    listedDate: date
    status: Literal["active", "pending", "sold"]
    description: str


class SearchFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    minPrice: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    maxPrice: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    minBedrooms: int | None = Field(default=None, ge=0)
    city: str | None = None
    keyword: str | None = None
    targetBudget: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    page: int = Field(default=1, ge=1)
    pageSize: int = PAGE_SIZE

    @field_validator("city", "keyword")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None

    @field_validator("pageSize")
    @classmethod
    def fixed_page_size(cls, value: int) -> int:
        if value != PAGE_SIZE:
            raise ValueError(f"pageSize is fixed at {PAGE_SIZE}.")
        return value

    @model_validator(mode="after")
    def valid_price_range(self) -> Self:
        if (
            self.minPrice is not None
            and self.maxPrice is not None
            and self.minPrice > self.maxPrice
        ):
            raise ValueError("minPrice must be less than or equal to maxPrice.")
        return self


class RankedListing(Listing):
    relevanceScore: float
    budgetScore: float | None
    recencyScore: float


class SearchResponse(BaseModel):
    items: list[RankedListing]
    total: int
    page: int
    pageSize: int
    totalPages: int
    scoringDate: date
