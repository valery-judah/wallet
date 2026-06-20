from __future__ import annotations

from wallet.api.deps import build_container
from wallet.bootstrap.spending_categories import seed_default_spending_categories
from wallet.config import Settings
from wallet.infrastructure.memory import InMemorySpendingCategoryRepository


def test_seed_default_spending_categories_populates_empty_repository() -> None:
    categories = InMemorySpendingCategoryRepository()

    seed_default_spending_categories(categories)

    seeded = categories.list()
    assert [category.name for category in seeded if category.parent_id is None] == [
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
    assert categories.get("category_food") is not None
    assert categories.get("category_food_groceries") is not None
    assert categories.get("category_other_miscellaneous") is not None


def test_seed_default_spending_categories_is_noop_for_non_empty_repository() -> None:
    categories = InMemorySpendingCategoryRepository()
    seed_default_spending_categories(categories)
    original_ids = [category.id for category in categories.list()]

    seed_default_spending_categories(categories)

    assert [category.id for category in categories.list()] == original_ids


def test_build_container_seeds_categories_during_container_creation() -> None:
    container = build_container(
        Settings(
            app_name="Wallet Test API",
            environment="test",
            debug=False,
            api_v1_prefix="/api/v1",
            frontend_host="http://localhost:5173",
        )
    )

    assert container.spending_categories.get("category_food") is not None
    assert container.spending_categories.get("category_food_groceries") is not None
