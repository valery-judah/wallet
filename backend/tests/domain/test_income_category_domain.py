from __future__ import annotations

import pytest

from wallet.domain.income_categories import IncomeCategory


def test_create_normalizes_income_category_name_and_optional_fields() -> None:
    category = IncomeCategory.create(
        id="income_salary",
        name="  Salary  ",
        parent_id=None,
        icon=" wallet ",
        color=" #55ccaa ",
        sort_order=10,
    )

    assert category.name == "Salary"
    assert category.normalized_name == "salary"
    assert category.icon == "wallet"
    assert category.color == "#55ccaa"


def test_create_rejects_self_parenting_income_category() -> None:
    with pytest.raises(ValueError, match="income category parent id must not equal category id"):
        IncomeCategory.create(
            id="income_salary",
            name="Salary",
            parent_id="income_salary",
            icon=None,
            color=None,
            sort_order=10,
        )
