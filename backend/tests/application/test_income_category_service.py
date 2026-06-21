from __future__ import annotations

import pytest

from wallet.application.income_categories import (
    CreateIncomeCategory,
    CreateIncomeCategoryRejectedError,
    IncomeCategoryService,
    UpdateIncomeCategory,
    UpdateIncomeCategoryRejectedError,
)
from wallet.infrastructure.memory import InMemoryIncomeCategoryRepository


def test_create_and_list_income_categories_returns_sorted_tree() -> None:
    service = _build_service()
    service.create_income_category(
        CreateIncomeCategory(name="Investments", sort_order=20),
    )
    work = service.create_income_category(
        CreateIncomeCategory(name="Work", sort_order=10),
    )
    service.create_income_category(
        CreateIncomeCategory(name="Bonus", parent_id=work.id, sort_order=20),
    )
    service.create_income_category(
        CreateIncomeCategory(name="Salary", parent_id=work.id, sort_order=10),
    )

    tree = service.list_income_categories()

    assert [node.category.name for node in tree] == ["Work", "Investments"]
    assert [node.category.name for node in tree[0].children] == ["Salary", "Bonus"]


def test_create_income_category_given_grandchild_parent_is_rejected() -> None:
    service = _build_service()
    work = service.create_income_category(CreateIncomeCategory(name="Work"))
    salary = service.create_income_category(
        CreateIncomeCategory(name="Salary", parent_id=work.id),
    )

    with pytest.raises(
        CreateIncomeCategoryRejectedError,
        match="category hierarchy supports only two levels",
    ):
        service.create_income_category(
            CreateIncomeCategory(name="Monthly Salary", parent_id=salary.id),
        )


def test_create_income_category_given_duplicate_sibling_name_is_rejected() -> None:
    service = _build_service()
    work = service.create_income_category(CreateIncomeCategory(name="Work"))
    service.create_income_category(
        CreateIncomeCategory(name="Salary", parent_id=work.id),
    )

    with pytest.raises(
        CreateIncomeCategoryRejectedError,
        match="category name must be unique within its sibling group",
    ):
        service.create_income_category(
            CreateIncomeCategory(name=" salary ", parent_id=work.id),
        )


def test_update_income_category_rejects_moving_parent_with_children_under_another_parent() -> None:
    service = _build_service()
    work = service.create_income_category(CreateIncomeCategory(name="Work"))
    service.create_income_category(
        CreateIncomeCategory(name="Salary", parent_id=work.id),
    )
    investments = service.create_income_category(CreateIncomeCategory(name="Investments"))

    with pytest.raises(
        UpdateIncomeCategoryRejectedError,
        match="category with children cannot become a child category",
    ):
        service.update_income_category(
            UpdateIncomeCategory(
                category_id=work.id,
                parent_id=investments.id,
                parent_id_provided=True,
            )
        )


def _build_service() -> IncomeCategoryService:
    ids = [
        "income_1",
        "income_2",
        "income_3",
        "income_4",
        "income_5",
        "income_6",
    ]
    return IncomeCategoryService(
        categories=InMemoryIncomeCategoryRepository(),
        generate_category_id=lambda: ids.pop(0),
    )
