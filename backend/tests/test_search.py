from datetime import timedelta

import pytest

from backend.app.models import PAGE_SIZE, SearchFilters
from backend.app.search import PageOutOfRange, score_listing, search_listings


def test_default_search_ranks_globally_before_pagination(listings, today):
    # Expected global recency order, independent of the input feed order.
    expected_ids = ["A5", "A4", "A2", "A3", "B8", "A1", "B7", "B9", "B10", "B11", "A6", "A7"]
    expected_pages = [expected_ids[start : start + PAGE_SIZE] for start in range(0, len(expected_ids), PAGE_SIZE)]
    all_items = []
    for page, expected in enumerate(expected_pages, start=1):
        result = search_listings(listings, SearchFilters(page=page), as_of=today)
        assert (result.total, result.totalPages, result.pageSize) == (12, len(expected_pages), PAGE_SIZE)
        assert [item.id for item in result.items] == expected
        all_items.extend(result.items)
    scores = [item.relevanceScore for item in all_items]
    assert scores == sorted(scores, reverse=True)
    keys = [(item.source, item.id) for item in all_items]
    assert len(set(keys)) == 12
    assert any(item.status == "pending" for item in all_items)


def test_combined_filters_are_inclusive_and_normalized(listings, today):
    result = search_listings(
        listings,
        SearchFilters(minPrice=525000, maxPrice=527500, minBedrooms=3, city=" sPrInGfIeLd ", keyword=" FENCED "),
        as_of=today,
    )
    assert {item.id for item in result.items} == {"A2", "B8"}
    assert result.total == 2


@pytest.mark.parametrize("filters", [
    {"city": "Spring"}, {"city": "Atlantis"}, {"keyword": "not in any description"},
    {"minPrice": 9999999}, {"maxPrice": 0}, {"minBedrooms": 99},
    {"city": "Reston", "keyword": "Metro"},
])
def test_no_matches_are_a_valid_empty_result(listings, today, filters):
    result = search_listings(listings, SearchFilters(**filters), as_of=today)
    assert result.items == []
    assert (result.total, result.totalPages, result.page) == (0, 0, 1)


def test_keyword_is_description_only_and_a_literal_substring(listings, today):
    assert search_listings(listings, SearchFilters(keyword="123 Main"), as_of=today).total == 0
    result = search_listings(listings, SearchFilters(keyword="pets"), as_of=today)
    assert result.total == 7  # Includes "no pets"; substring search has no semantic inference.


def test_blank_text_and_zero_filters_are_not_dropped(listings, today):
    assert search_listings(listings, SearchFilters(city="  ", keyword=" ", minPrice=0, minBedrooms=0), as_of=today).total == 12


def test_score_formula_and_budget_symmetry(listings, today):
    template = listings[0].model_copy(update={"listedDate": today - timedelta(days=90)})
    exact = template.model_copy(update={"price": 500000})
    below = template.model_copy(update={"price": 450000})
    above = template.model_copy(update={"price": 550000})
    assert score_listing(exact, 500000, today) == (85, 100, 50)
    assert score_listing(below, 500000, today) == score_listing(above, 500000, today)
    assert score_listing(below, 500000, today)[0] == pytest.approx(78)


@pytest.mark.parametrize("age_days,expected_score", [(0, 100), (365, 50), (730, 25)])
def test_recency_without_budget_uses_365_day_half_life(listings, today, age_days, expected_score):
    listing = listings[0].model_copy(update={"listedDate": today - timedelta(days=age_days)})
    assert score_listing(listing, None, today) == (expected_score, None, expected_score)


def test_budget_presence_selects_recency_half_life(listings, today):
    listing = listings[0].model_copy(update={"listedDate": today - timedelta(days=365)})
    assert score_listing(listing, None, today)[2] == 50
    assert score_listing(listing, listing.price, today)[2] == pytest.approx(100 * 2 ** (-365 / 90))


def test_scores_are_bounded_and_future_dates_have_zero_age(listings, today):
    future = listings[0].model_copy(update={"listedDate": today + timedelta(days=5)})
    assert score_listing(future, future.price, today) == (100, 100, 100)
    assert score_listing(future, 1, today) == (30, 0, 100)
    old = future.model_copy(update={"listedDate": today - timedelta(days=9000)})
    score, _, _ = score_listing(old, 1, today)
    assert 0 <= score <= 100


def test_budget_affects_ranking_without_excluding_listings(listings, today):
    result = search_listings(listings, SearchFilters(targetBudget=450000), as_of=today)
    assert result.items[0].id == "A1"
    assert result.total == 12


def test_ties_use_date_source_and_id_independent_of_input_order(listings, today):
    template = listings[0].model_copy(update={"price": 500000})
    # Future dates all get recency 100, so date is a meaningful secondary tie-break.
    records = [
        template.model_copy(update={"source": "MLS_B", "id": "1", "listedDate": today}),
        template.model_copy(update={"source": "MLS_A", "id": "2", "listedDate": today}),
        template.model_copy(update={"source": "MLS_A", "id": "1", "listedDate": today}),
        template.model_copy(update={"source": "MLS_Z", "id": "9", "listedDate": today + timedelta(days=1)}),
    ]
    expected = [("MLS_Z", "9"), ("MLS_A", "1"), ("MLS_A", "2"), ("MLS_B", "1")]
    expected_pages = [expected[start : start + PAGE_SIZE] for start in range(0, len(expected), PAGE_SIZE)]
    for data in [records, list(reversed(records))]:
        for page, expected_items in enumerate(expected_pages, start=1):
            result = search_listings(data, SearchFilters(targetBudget=500000, page=page), as_of=today)
            assert [(item.source, item.id) for item in result.items] == expected_items
            assert all(item.relevanceScore == 100 for item in result.items)


def test_same_id_across_sources_and_same_property_are_preserved(listings, today):
    records = [listings[0], listings[0].model_copy(update={"source": "MLS_B"})]
    assert search_listings(records, SearchFilters(), as_of=today).total == 2
    assert search_listings(listings, SearchFilters(city="Fairfax"), as_of=today).total == 2


@pytest.mark.parametrize("count,expected_pages,last_count", [
    (1, 1, 1),
    (PAGE_SIZE, 1, PAGE_SIZE),
    (PAGE_SIZE + 1, 2, 1),
    (2 * PAGE_SIZE, 2, PAGE_SIZE),
    (2 * PAGE_SIZE + 1, 3, 1),
    (4 * PAGE_SIZE, 4, PAGE_SIZE),
])
def test_pagination_boundaries(listings, today, count, expected_pages, last_count):
    records = [listings[index % len(listings)].model_copy(update={"id": f"test-{index}"}) for index in range(count)]
    result = search_listings(records, SearchFilters(page=expected_pages), as_of=today)
    assert result.total == count
    assert result.totalPages == expected_pages
    assert len(result.items) == last_count
    with pytest.raises(PageOutOfRange):
        search_listings(records, SearchFilters(page=expected_pages + 1), as_of=today)


def test_empty_dataset_page_one_only(today):
    assert search_listings([], SearchFilters(), as_of=today).total == 0
    with pytest.raises(PageOutOfRange):
        search_listings([], SearchFilters(page=2), as_of=today)
