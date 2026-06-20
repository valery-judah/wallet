from __future__ import annotations

from dataclasses import dataclass

from wallet.application.spending_categories import CreateSpendingCategory, SpendingCategoryService
from wallet.ports.spending_categories import SpendingCategoryRepository


@dataclass(frozen=True, slots=True)
class DefaultSpendingCategorySeed:
    id: str
    name: str
    sort_order: int
    icon: str | None = None
    color: str | None = None
    children: tuple[DefaultSpendingCategorySeed, ...] = ()


def seed_default_spending_categories(categories: SpendingCategoryRepository) -> None:
    if categories.list():
        return

    service = SpendingCategoryService(categories=categories)
    for root in DEFAULT_SPENDING_CATEGORY_SEEDS:
        service.create_spending_category(
            CreateSpendingCategory(
                category_id=root.id,
                name=root.name,
                icon=root.icon,
                color=root.color,
                sort_order=root.sort_order,
            )
        )
        for child in root.children:
            service.create_spending_category(
                CreateSpendingCategory(
                    category_id=child.id,
                    name=child.name,
                    parent_id=root.id,
                    icon=child.icon,
                    color=child.color,
                    sort_order=child.sort_order,
                )
            )


DEFAULT_SPENDING_CATEGORY_SEEDS: tuple[DefaultSpendingCategorySeed, ...] = (
    DefaultSpendingCategorySeed(
        id="category_food",
        name="Food",
        sort_order=10,
        children=(
            DefaultSpendingCategorySeed(
                id="category_food_groceries",
                name="Groceries",
                sort_order=10,
            ),
            DefaultSpendingCategorySeed(
                id="category_food_restaurants",
                name="Restaurants",
                sort_order=20,
            ),
            DefaultSpendingCategorySeed(
                id="category_food_coffee",
                name="Coffee",
                sort_order=30,
            ),
        ),
    ),
    DefaultSpendingCategorySeed(
        id="category_housing",
        name="Housing",
        sort_order=20,
        children=(
            DefaultSpendingCategorySeed(
                id="category_housing_rent",
                name="Rent",
                sort_order=10,
            ),
            DefaultSpendingCategorySeed(
                id="category_housing_utilities",
                name="Utilities",
                sort_order=20,
            ),
            DefaultSpendingCategorySeed(
                id="category_housing_home_maintenance",
                name="Home Maintenance",
                sort_order=30,
            ),
        ),
    ),
    DefaultSpendingCategorySeed(
        id="category_transport",
        name="Transport",
        sort_order=30,
        children=(
            DefaultSpendingCategorySeed(
                id="category_transport_fuel",
                name="Fuel",
                sort_order=10,
            ),
            DefaultSpendingCategorySeed(
                id="category_transport_public_transit",
                name="Public Transit",
                sort_order=20,
            ),
            DefaultSpendingCategorySeed(
                id="category_transport_rideshare",
                name="Rideshare",
                sort_order=30,
            ),
            DefaultSpendingCategorySeed(
                id="category_transport_parking",
                name="Parking",
                sort_order=40,
            ),
        ),
    ),
    DefaultSpendingCategorySeed(
        id="category_shopping",
        name="Shopping",
        sort_order=40,
        children=(
            DefaultSpendingCategorySeed(
                id="category_shopping_clothing",
                name="Clothing",
                sort_order=10,
            ),
            DefaultSpendingCategorySeed(
                id="category_shopping_electronics",
                name="Electronics",
                sort_order=20,
            ),
            DefaultSpendingCategorySeed(
                id="category_shopping_household_items",
                name="Household Items",
                sort_order=30,
            ),
        ),
    ),
    DefaultSpendingCategorySeed(
        id="category_health",
        name="Health",
        sort_order=50,
        children=(
            DefaultSpendingCategorySeed(
                id="category_health_pharmacy",
                name="Pharmacy",
                sort_order=10,
            ),
            DefaultSpendingCategorySeed(
                id="category_health_medical",
                name="Medical",
                sort_order=20,
            ),
            DefaultSpendingCategorySeed(
                id="category_health_fitness",
                name="Fitness",
                sort_order=30,
            ),
        ),
    ),
    DefaultSpendingCategorySeed(
        id="category_entertainment",
        name="Entertainment",
        sort_order=60,
        children=(
            DefaultSpendingCategorySeed(
                id="category_entertainment_streaming",
                name="Streaming",
                sort_order=10,
            ),
            DefaultSpendingCategorySeed(
                id="category_entertainment_movies",
                name="Movies",
                sort_order=20,
            ),
            DefaultSpendingCategorySeed(
                id="category_entertainment_games",
                name="Games",
                sort_order=30,
            ),
            DefaultSpendingCategorySeed(
                id="category_entertainment_events",
                name="Events",
                sort_order=40,
            ),
        ),
    ),
    DefaultSpendingCategorySeed(
        id="category_travel",
        name="Travel",
        sort_order=70,
        children=(
            DefaultSpendingCategorySeed(
                id="category_travel_flights",
                name="Flights",
                sort_order=10,
            ),
            DefaultSpendingCategorySeed(
                id="category_travel_hotels",
                name="Hotels",
                sort_order=20,
            ),
            DefaultSpendingCategorySeed(
                id="category_travel_local_transport",
                name="Local Transport",
                sort_order=30,
            ),
        ),
    ),
    DefaultSpendingCategorySeed(
        id="category_education",
        name="Education",
        sort_order=80,
        children=(
            DefaultSpendingCategorySeed(
                id="category_education_books",
                name="Books",
                sort_order=10,
            ),
            DefaultSpendingCategorySeed(
                id="category_education_courses",
                name="Courses",
                sort_order=20,
            ),
        ),
    ),
    DefaultSpendingCategorySeed(
        id="category_personal",
        name="Personal",
        sort_order=90,
        children=(
            DefaultSpendingCategorySeed(
                id="category_personal_haircuts",
                name="Haircuts",
                sort_order=10,
            ),
            DefaultSpendingCategorySeed(
                id="category_personal_personal_care",
                name="Personal Care",
                sort_order=20,
            ),
        ),
    ),
    DefaultSpendingCategorySeed(
        id="category_pets",
        name="Pets",
        sort_order=100,
        children=(
            DefaultSpendingCategorySeed(
                id="category_pets_pet_food",
                name="Pet Food",
                sort_order=10,
            ),
            DefaultSpendingCategorySeed(
                id="category_pets_veterinary",
                name="Veterinary",
                sort_order=20,
            ),
        ),
    ),
    DefaultSpendingCategorySeed(
        id="category_fees",
        name="Fees",
        sort_order=110,
        children=(
            DefaultSpendingCategorySeed(
                id="category_fees_bank_fees",
                name="Bank Fees",
                sort_order=10,
            ),
            DefaultSpendingCategorySeed(
                id="category_fees_service_fees",
                name="Service Fees",
                sort_order=20,
            ),
        ),
    ),
    DefaultSpendingCategorySeed(
        id="category_gifts_and_donations",
        name="Gifts & Donations",
        sort_order=120,
        children=(
            DefaultSpendingCategorySeed(
                id="category_gifts_and_donations_gifts",
                name="Gifts",
                sort_order=10,
            ),
            DefaultSpendingCategorySeed(
                id="category_gifts_and_donations_donations",
                name="Donations",
                sort_order=20,
            ),
        ),
    ),
    DefaultSpendingCategorySeed(
        id="category_taxes",
        name="Taxes",
        sort_order=130,
        children=(
            DefaultSpendingCategorySeed(
                id="category_taxes_income_tax",
                name="Income Tax",
                sort_order=10,
            ),
            DefaultSpendingCategorySeed(
                id="category_taxes_property_tax",
                name="Property Tax",
                sort_order=20,
            ),
        ),
    ),
    DefaultSpendingCategorySeed(
        id="category_other",
        name="Other",
        sort_order=140,
        children=(
            DefaultSpendingCategorySeed(
                id="category_other_miscellaneous",
                name="Miscellaneous",
                sort_order=10,
            ),
        ),
    ),
)
