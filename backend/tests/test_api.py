import json

import pytest
from pydantic import ValidationError

from backend.app.models import PAGE_SIZE
from backend.app.seed import DATA_PATH, load_listings


def test_response_contract_and_second_page(client):
    first = client.get("/api/listings").json()
    assert first.keys() == {"items", "total", "page", "pageSize", "totalPages", "scoringDate"}
    assert first["scoringDate"] == "2026-11-10"
    assert first["pageSize"] == PAGE_SIZE
    assert len(first["items"]) == PAGE_SIZE
    assert first["items"][0]["budgetScore"] is None
    response = client.get("/api/listings", params={"page": 2, "targetBudget": 450000})
    assert response.status_code == 200
    assert response.json()["page"] == 2
    assert all(item["budgetScore"] is not None for item in response.json()["items"])


def test_api_combines_filters(client):
    response = client.get("/api/listings", params={
        "city": " SPRINGFIELD ", "keyword": " Fenced ", "minPrice": 525000,
        "maxPrice": 527500, "minBedrooms": 3, "targetBudget": 525000,
    })
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["A2", "B8"]


@pytest.mark.parametrize("params", [
    {"minPrice": -1}, {"maxPrice": -1}, {"minBedrooms": -1},
    {"minBedrooms": 2.5}, {"targetBudget": 0}, {"targetBudget": -1},
    {"minPrice": 500000, "maxPrice": 400000}, {"minPrice": "abc"},
    {"targetBudget": "nan"}, {"maxPrice": "inf"}, {"targetBudget": "-inf"},
    {"page": 0}, {"page": -1}, {"page": 1.5}, {"page": "abc"},
    {"city": "Atlantis", "page": 2},
    {"pageSize": 0}, {"pageSize": -1}, {"pageSize": PAGE_SIZE + 1},
    {"pageSize": "abc"}, {"unknownFilter": "value"},
])
def test_invalid_input_returns_structured_422(client, params):
    response = client.get("/api/listings", params=params)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)
    assert all(error["msg"] and error["loc"][0] == "query" for error in response.json()["detail"])


def test_no_matches_are_success_not_validation_failure(client):
    response = client.get("/api/listings", params={"city": "Atlantis"})
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["totalPages"] == 0


def test_explicit_fixed_page_size_is_accepted(client):
    response = client.get("/api/listings", params={"pageSize": PAGE_SIZE})
    assert response.status_code == 200
    assert response.json()["pageSize"] == PAGE_SIZE


def test_all_valid_pages_and_first_out_of_range_page(client, listings):
    expected_pages = [listings[start : start + PAGE_SIZE] for start in range(0, len(listings), PAGE_SIZE)]
    for page, expected_items in enumerate(expected_pages, start=1):
        response = client.get("/api/listings", params={"page": page})
        assert response.status_code == 200
        result = response.json()
        assert result["page"] == page
        assert result["totalPages"] == len(expected_pages)
        assert len(result["items"]) == len(expected_items)

    response = client.get("/api/listings", params={"page": len(expected_pages) + 1})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "page"]


def test_loader_preserves_provided_data():
    assert len(load_listings(DATA_PATH)) == 12


def test_loader_rejects_duplicate_composite_ids_but_allows_cross_source_ids(tmp_path):
    listing = json.loads(DATA_PATH.read_text())[0]
    path = tmp_path / "listings.json"
    path.write_text(json.dumps([listing, listing]))
    with pytest.raises(ValueError, match="duplicate"):
        load_listings(path)
    path.write_text(json.dumps([listing, {**listing, "source": "MLS_B"}]))
    assert len(load_listings(path)) == 2


def test_loader_rejects_malformed_listing(tmp_path):
    path = tmp_path / "listings.json"
    path.write_text('[{"id": "bad"}]')
    with pytest.raises(ValidationError):
        load_listings(path)
