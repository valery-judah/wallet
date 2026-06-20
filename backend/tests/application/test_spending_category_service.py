from __future__ import annotations

import pytest

from wallet.application.spending_categories import (
    CreateSpendingCategory,
    CreateSpendingCategoryRejectedError,
    SpendingCategoryService,
    UpdateSpendingCategory,
    UpdateSpendingCategoryRejectedError,
)
from wallet.infrastructure.memory import InMemorySpendingCategoryRepository


def test_create_and_list_spending_categories_returns_sorted_tree() -> None:
    service = _build_service()
    travel = service.create_spending_category(
        CreateSpendingCategory(name="Travel", sort_order=20),
    )
    food = service.create_spending_category(
        CreateSpendingCategory(name="Food", sort_order=10),
    )
    service.create_spending_category(
        CreateSpendingCategory(name="Restaurants", parent_id=food.id, sort_order=20),
    )
    service.create_spending_category(
        CreateSpendingCategory(name="Groceries", parent_id=food.id, sort_order=10),
    )

    tree = service.list_spending_categories()

    assert [node.category.name for node in tree] == ["Food", "Travel"]
    assert [node.category.name for node in tree[0].children] == ["Groceries", "Restaurants"]
    assert tree[1].category.id == travel.id


def test_create_spending_category_given_grandchild_parent_is_rejected() -> None:
    service = _build_service()
    food = service.create_spending_category(CreateSpendingCategory(name="Food"))
    groceries = service.create_spending_category(
        CreateSpendingCategory(name="Groceries", parent_id=food.id),
    )

    with pytest.raises(
        CreateSpendingCategoryRejectedError,
        match="category hierarchy supports only two levels",
    ):
        service.create_spending_category(
            CreateSpendingCategory(name="Organic Produce", parent_id=groceries.id),
        )


def test_create_spending_category_given_duplicate_sibling_name_is_rejected() -> None:
    service = _build_service()
    food = service.create_spending_category(CreateSpendingCategory(name="Food"))
    service.create_spending_category(
        CreateSpendingCategory(name="Groceries", parent_id=food.id),
    )

    with pytest.raises(
        CreateSpendingCategoryRejectedError,
        match="category name must be unique within its sibling group",
    ):
        service.create_spending_category(
            CreateSpendingCategory(name=" groceries ", parent_id=food.id),
        )


def test_create_spending_category_accepts_explicit_internal_category_id() -> None:
    service = _build_service()

    category = service.create_spending_category(
        CreateSpendingCategory(
            category_id="category_food",
            name="Food",
            sort_order=10,
        )
    )

    assert category.id == "category_food"


def test_create_spending_category_rejects_duplicate_explicit_category_id() -> None:
    service = _build_service()
    service.create_spending_category(
        CreateSpendingCategory(
            category_id="category_food",
            name="Food",
            sort_order=10,
        )
    )

    with pytest.raises(
        CreateSpendingCategoryRejectedError,
        match="category id already exists",
    ):
        service.create_spending_category(
            CreateSpendingCategory(
                category_id="category_food",
                name="Housing",
                sort_order=20,
            )
        )


def test_update_spending_category_rejects_moving_parent_with_children_under_another_parent() -> (
    None
):
    service = _build_service()
    food = service.create_spending_category(CreateSpendingCategory(name="Food"))
    service.create_spending_category(
        CreateSpendingCategory(name="Groceries", parent_id=food.id),
    )
    transport = service.create_spending_category(CreateSpendingCategory(name="Transport"))

    with pytest.raises(
        UpdateSpendingCategoryRejectedError,
        match="category with children cannot become a child category",
    ):
        service.update_spending_category(
            UpdateSpendingCategory(
                category_id=food.id,
                parent_id=transport.id,
                parent_id_provided=True,
            )
        )


def _build_service() -> SpendingCategoryService:
    ids = [
        "category_1",
        "category_2",
        "category_3",
        "category_4",
        "category_5",
        "category_6",
        "category_7",
        "category_8",
        "category_9",
        "category_10",
    ]
    return SpendingCategoryService(
        categories=InMemorySpendingCategoryRepository(),
        generate_category_id=lambda: ids.pop(0),
    )
