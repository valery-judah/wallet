from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from wallet.api.app import create_app
from wallet.config import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(
        Settings(
            app_name="Wallet Test API",
            environment="test",
            debug=False,
            api_v1_prefix="/api/v1",
            frontend_host="http://localhost:5173",
        )
    )

    with TestClient(app) as test_client:
        yield test_client


def test_list_spending_categories_returns_seeded_default_tree(client: TestClient) -> None:
    response = client.get("/api/v1/spending-categories")

    assert response.status_code == 200
    body = response.json()
    assert [category["name"] for category in body] == [
        "Food",
        "Housing",
        "Transport",
        "Shopping",
        "Health",
        "Entertainment",
        "Travel",
        "Education",
        "Personal",
        "Pets",
        "Fees",
        "Gifts & Donations",
        "Taxes",
        "Other",
    ]
    assert body[0]["id"] == "category_food"
    assert [child["name"] for child in body[0]["children"]] == [
        "Groceries",
        "Restaurants",
        "Coffee",
    ]
    assert body[0]["children"][0]["id"] == "category_food_groceries"


def test_create_spending_category_supports_root_and_child_categories(client: TestClient) -> None:
    root_response = client.post(
        "/api/v1/spending-categories",
        json={"name": "Bills", "sort_order": 150},
    )
    root_id = root_response.json()["id"]
    child_response = client.post(
        "/api/v1/spending-categories",
        json={"name": "Internet", "parent_id": root_id, "sort_order": 10},
    )
    list_response = client.get("/api/v1/spending-categories")
    bills = _find_category(list_response.json(), "Bills")

    assert root_response.status_code == 201
    assert child_response.status_code == 201
    assert bills["children"][0]["name"] == "Internet"


def test_create_spending_category_rejects_grandchildren(client: TestClient) -> None:
    categories = client.get("/api/v1/spending-categories").json()
    food = _find_category(categories, "Food")
    groceries = _find_child(food, "Groceries")

    response = client.post(
        "/api/v1/spending-categories",
        json={"name": "Organic Produce", "parent_id": groceries["id"]},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "category hierarchy supports only two levels"}


def test_create_spending_category_rejects_duplicate_sibling_name(client: TestClient) -> None:
    categories = client.get("/api/v1/spending-categories").json()
    food = _find_category(categories, "Food")

    response = client.post(
        "/api/v1/spending-categories",
        json={"name": " groceries ", "parent_id": food["id"]},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "category name must be unique within its sibling group",
    }


def test_patch_spending_category_updates_name_parent_and_sort_order(client: TestClient) -> None:
    create_bills = client.post(
        "/api/v1/spending-categories",
        json={"name": "Bills", "sort_order": 200},
    )
    create_streaming = client.post(
        "/api/v1/spending-categories",
        json={"name": "Subscriptions", "sort_order": 210},
    )
    bills_id = create_bills.json()["id"]
    streaming_id = create_streaming.json()["id"]

    response = client.patch(
        f"/api/v1/spending-categories/{streaming_id}",
        json={"name": "Streaming Bills", "parent_id": bills_id, "sort_order": 5},
    )
    list_response = client.get("/api/v1/spending-categories")
    bills = _find_category(list_response.json(), "Bills")

    assert response.status_code == 200
    assert response.json()["name"] == "Streaming Bills"
    assert response.json()["parent_id"] == bills_id
    assert bills["children"][0]["name"] == "Streaming Bills"


def test_missing_spending_category_returns_not_found(client: TestClient) -> None:
    response = client.patch("/api/v1/spending-categories/missing", json={"name": "Missing"})

    assert response.status_code == 404
    assert response.json() == {"detail": "spending category not found: missing"}


def test_openapi_schema_exposes_spending_category_routes(client: TestClient) -> None:
    schema = client.app.openapi()

    assert schema["paths"]["/api/v1/spending-categories"]["get"]["tags"] == ["spending-categories"]
    assert (
        schema["paths"]["/api/v1/spending-categories"]["get"]["operationId"]
        == "spending-categories-list_spending_categories"
    )
    assert (
        schema["paths"]["/api/v1/spending-categories"]["post"]["operationId"]
        == "spending-categories-create_spending_category"
    )
    assert (
        schema["paths"]["/api/v1/spending-categories/{category_id}"]["patch"]["operationId"]
        == "spending-categories-update_spending_category"
    )


def _find_category(categories: list[dict[str, object]], name: str) -> dict[str, object]:
    for category in categories:
        if category["name"] == name:
            return category
    raise AssertionError(f"category not found in response: {name}")


def _find_child(category: dict[str, object], name: str) -> dict[str, object]:
    children = category["children"]
    assert isinstance(children, list)
    for child in children:
        if child["name"] == name:
            return child
    raise AssertionError(f"child category not found in response: {name}")
