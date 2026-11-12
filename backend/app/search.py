"""Filtering, scoring, and pagination, independent of HTTP and the system clock."""

from collections.abc import Sequence
from datetime import date
from math import ceil

from .models import PAGE_SIZE, Listing, RankedListing, SearchFilters, SearchResponse


class PageOutOfRange(ValueError):
    pass


def score_listing(
    listing: Listing, target_budget: float | None, as_of: date
) -> tuple[float, float | None, float]:
    age_days = max(0, (as_of - listing.listedDate).days)
    half_life_days = 365 if target_budget is None else 90
    recency = 2 ** (-age_days / half_life_days)
    budget = (
        max(0.0, 1 - abs(listing.price - target_budget) / target_budget)
        if target_budget is not None
        else None
    )
    relevance = recency if budget is None else 0.7 * budget + 0.3 * recency
    return relevance * 100, budget * 100 if budget is not None else None, recency * 100


def search_listings(
    listings: Sequence[Listing], filters: SearchFilters, *, as_of: date
) -> SearchResponse:
    city = filters.city.casefold() if filters.city else None
    keyword = filters.keyword.casefold() if filters.keyword else None
    ranked: list[tuple[Listing, float, float | None, float]] = []

    for listing in listings:
        if filters.minPrice is not None and listing.price < filters.minPrice:
            continue
        if filters.maxPrice is not None and listing.price > filters.maxPrice:
            continue
        if filters.minBedrooms is not None and listing.bedrooms < filters.minBedrooms:
            continue
        if city and listing.city.strip().casefold() != city:
            continue
        if keyword and keyword not in listing.description.casefold():
            continue
        score, budget, recency = score_listing(listing, filters.targetBudget, as_of)
        ranked.append((listing, score, budget, recency))

    # Sort before rounding and slicing; deterministic even if feed order changes.
    ranked.sort(key=lambda row: (-row[1], -row[0].listedDate.toordinal(), row[0].source, row[0].id))
    total = len(ranked)
    total_pages = ceil(total / PAGE_SIZE)
    if filters.page > max(1, total_pages):
        raise PageOutOfRange(f"Page must be between 1 and {max(1, total_pages)}.")

    start = (filters.page - 1) * PAGE_SIZE
    items = [
        RankedListing(
            **listing.model_dump(),
            relevanceScore=round(score, 4),
            budgetScore=round(budget, 4) if budget is not None else None,
            recencyScore=round(recency, 4),
        )
        for listing, score, budget, recency in ranked[start : start + PAGE_SIZE]
    ]
    return SearchResponse(
        items=items,
        total=total,
        page=filters.page,
        pageSize=PAGE_SIZE,
        totalPages=total_pages,
        scoringDate=as_of,
    )
