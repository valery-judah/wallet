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


def test_list_income_categories_returns_seeded_default_tree(client: TestClient) -> None:
    response = client.get("/api/v1/income-categories")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["name"] == "Salary"
    assert [child["name"] for child in body[0]["children"]] == [
        "Payroll",
        "Bonus",
    ]


def test_create_income_category_supports_root_and_child_categories(client: TestClient) -> None:
    root_response = client.post(
        "/api/v1/income-categories",
        json={"name": "Work", "sort_order": 150},
    )
    root_id = root_response.json()["id"]
    child_response = client.post(
        "/api/v1/income-categories",
        json={"name": "Freelance", "parent_id": root_id, "sort_order": 10},
    )
    list_response = client.get("/api/v1/income-categories")
    work = _find_category(list_response.json(), "Work")

    assert root_response.status_code == 201
    assert child_response.status_code == 201
    assert work["children"][0]["name"] == "Freelance"


def test_patch_income_category_updates_name_parent_and_sort_order(client: TestClient) -> None:
    create_work = client.post(
        "/api/v1/income-categories",
        json={"name": "Work", "sort_order": 200},
    )
    create_sales = client.post(
        "/api/v1/income-categories",
        json={"name": "Sales", "sort_order": 210},
    )
    work_id = create_work.json()["id"]
    sales_id = create_sales.json()["id"]

    response = client.patch(
        f"/api/v1/income-categories/{sales_id}",
        json={"name": "Contracts", "parent_id": work_id, "sort_order": 5},
    )
    list_response = client.get("/api/v1/income-categories")
    work = _find_category(list_response.json(), "Work")

    assert response.status_code == 200
    assert response.json()["name"] == "Contracts"
    assert response.json()["parent_id"] == work_id
    assert work["children"][0]["name"] == "Contracts"


def _find_category(categories: list[dict[str, object]], name: str) -> dict[str, object]:
    for category in categories:
        if category["name"] == name:
            return category
    raise AssertionError(f"category not found in response: {name}")
