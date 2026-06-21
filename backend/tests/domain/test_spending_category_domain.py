from __future__ import annotations

import pytest

from wallet.domain.spending_categories import SpendingCategory


def test_create_normalizes_category_name_and_optional_fields() -> None:
    category = SpendingCategory.create(
        id="category_food",
        name="  Food  ",
        parent_id=None,
        icon=" utensils ",
        color=" #ffcc00 ",
        sort_order=10,
    )

    assert category.name == "Food"
    assert category.normalized_name == "food"
    assert category.icon == "utensils"
    assert category.color == "#ffcc00"


def test_create_given_blank_optional_field_is_rejected() -> None:
    with pytest.raises(ValueError, match="spending category icon must not be blank"):
        SpendingCategory.create(
            id="category_food",
            name="Food",
            parent_id=None,
            icon="   ",
            color=None,
            sort_order=10,
        )
