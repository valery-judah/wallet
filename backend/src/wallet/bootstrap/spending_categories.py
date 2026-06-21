from __future__ import annotations

from dataclasses import dataclass

from wallet.application.income_categories import CreateIncomeCategory, IncomeCategoryService
from wallet.application.spending_categories import CreateSpendingCategory, SpendingCategoryService
from wallet.ports.income_categories import IncomeCategoryRepository
from wallet.ports.spending_categories import SpendingCategoryRepository


@dataclass(frozen=True, slots=True)
class DefaultCategorySeed:
    id: str
    name: str
    sort_order: int
    icon: str | None = None
    color: str | None = None
    children: tuple[DefaultCategorySeed, ...] = ()


def seed_default_spending_categories(categories: SpendingCategoryRepository) -> None:
    if categories.list():
        return

    service = SpendingCategoryService(categories=categories)
    _seed_spending_categories(service, DEFAULT_SPENDING_CATEGORY_SEEDS)


def seed_default_income_categories(categories: IncomeCategoryRepository) -> None:
    if categories.list():
        return

    service = IncomeCategoryService(categories=categories)
    _seed_income_categories(service, DEFAULT_INCOME_CATEGORY_SEEDS)


def seed_default_categories(
    spending_categories: SpendingCategoryRepository,
    income_categories: IncomeCategoryRepository,
) -> None:
    seed_default_spending_categories(spending_categories)
    seed_default_income_categories(income_categories)


def _seed_spending_categories(
    service: SpendingCategoryService,
    roots: tuple[DefaultCategorySeed, ...],
) -> None:
    for root in roots:
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


def _seed_income_categories(
    service: IncomeCategoryService,
    roots: tuple[DefaultCategorySeed, ...],
) -> None:
    for root in roots:
        service.create_income_category(
            CreateIncomeCategory(
                category_id=root.id,
                name=root.name,
                icon=root.icon,
                color=root.color,
                sort_order=root.sort_order,
            )
        )
        for child in root.children:
            service.create_income_category(
                CreateIncomeCategory(
                    category_id=child.id,
                    name=child.name,
                    parent_id=root.id,
                    icon=child.icon,
                    color=child.color,
                    sort_order=child.sort_order,
                )
            )


DEFAULT_SPENDING_CATEGORY_SEEDS: tuple[DefaultCategorySeed, ...] = (
    DefaultCategorySeed(
        id="category_food",
        name="Food",
        sort_order=10,
        children=(
            DefaultCategorySeed(
                id="category_food_groceries",
                name="Groceries",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="category_food_restaurants",
                name="Restaurants",
                sort_order=20,
            ),
            DefaultCategorySeed(
                id="category_food_coffee",
                name="Coffee",
                sort_order=30,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="category_housing",
        name="Housing",
        sort_order=20,
        children=(
            DefaultCategorySeed(
                id="category_housing_rent",
                name="Rent",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="category_housing_utilities",
                name="Utilities",
                sort_order=20,
            ),
            DefaultCategorySeed(
                id="category_housing_home_maintenance",
                name="Home Maintenance",
                sort_order=30,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="category_transport",
        name="Transport",
        sort_order=30,
        children=(
            DefaultCategorySeed(
                id="category_transport_fuel",
                name="Fuel",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="category_transport_public_transit",
                name="Public Transit",
                sort_order=20,
            ),
            DefaultCategorySeed(
                id="category_transport_rideshare",
                name="Rideshare",
                sort_order=30,
            ),
            DefaultCategorySeed(
                id="category_transport_parking",
                name="Parking",
                sort_order=40,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="category_shopping",
        name="Shopping",
        sort_order=40,
        children=(
            DefaultCategorySeed(
                id="category_shopping_clothing",
                name="Clothing",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="category_shopping_electronics",
                name="Electronics",
                sort_order=20,
            ),
            DefaultCategorySeed(
                id="category_shopping_household_items",
                name="Household Items",
                sort_order=30,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="category_health",
        name="Health",
        sort_order=50,
        children=(
            DefaultCategorySeed(
                id="category_health_pharmacy",
                name="Pharmacy",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="category_health_medical",
                name="Medical",
                sort_order=20,
            ),
            DefaultCategorySeed(
                id="category_health_fitness",
                name="Fitness",
                sort_order=30,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="category_entertainment",
        name="Entertainment",
        sort_order=60,
        children=(
            DefaultCategorySeed(
                id="category_entertainment_streaming",
                name="Streaming",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="category_entertainment_movies",
                name="Movies",
                sort_order=20,
            ),
            DefaultCategorySeed(
                id="category_entertainment_games",
                name="Games",
                sort_order=30,
            ),
            DefaultCategorySeed(
                id="category_entertainment_events",
                name="Events",
                sort_order=40,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="category_travel",
        name="Travel",
        sort_order=70,
        children=(
            DefaultCategorySeed(
                id="category_travel_flights",
                name="Flights",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="category_travel_hotels",
                name="Hotels",
                sort_order=20,
            ),
            DefaultCategorySeed(
                id="category_travel_local_transport",
                name="Local Transport",
                sort_order=30,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="category_education",
        name="Education",
        sort_order=80,
        children=(
            DefaultCategorySeed(
                id="category_education_books",
                name="Books",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="category_education_courses",
                name="Courses",
                sort_order=20,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="category_personal",
        name="Personal",
        sort_order=90,
        children=(
            DefaultCategorySeed(
                id="category_personal_haircuts",
                name="Haircuts",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="category_personal_personal_care",
                name="Personal Care",
                sort_order=20,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="category_pets",
        name="Pets",
        sort_order=100,
        children=(
            DefaultCategorySeed(
                id="category_pets_pet_food",
                name="Pet Food",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="category_pets_veterinary",
                name="Veterinary",
                sort_order=20,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="category_fees",
        name="Fees",
        sort_order=110,
        children=(
            DefaultCategorySeed(
                id="category_fees_bank_fees",
                name="Bank Fees",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="category_fees_service_fees",
                name="Service Fees",
                sort_order=20,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="category_gifts_and_donations",
        name="Gifts & Donations",
        sort_order=120,
        children=(
            DefaultCategorySeed(
                id="category_gifts_and_donations_gifts",
                name="Gifts",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="category_gifts_and_donations_donations",
                name="Donations",
                sort_order=20,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="category_taxes",
        name="Taxes",
        sort_order=130,
        children=(
            DefaultCategorySeed(
                id="category_taxes_income_tax",
                name="Income Tax",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="category_taxes_property_tax",
                name="Property Tax",
                sort_order=20,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="category_other",
        name="Other",
        sort_order=140,
        children=(
            DefaultCategorySeed(
                id="category_other_miscellaneous",
                name="Miscellaneous",
                sort_order=10,
            ),
        ),
    ),
)

DEFAULT_INCOME_CATEGORY_SEEDS: tuple[DefaultCategorySeed, ...] = (
    DefaultCategorySeed(
        id="income_salary",
        name="Salary",
        sort_order=10,
        children=(
            DefaultCategorySeed(
                id="income_salary_payroll",
                name="Payroll",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="income_salary_bonus",
                name="Bonus",
                sort_order=20,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="income_business",
        name="Business",
        sort_order=20,
        children=(
            DefaultCategorySeed(
                id="income_business_sales",
                name="Sales",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="income_business_contracts",
                name="Contracts",
                sort_order=20,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="income_investments",
        name="Investments",
        sort_order=30,
        children=(
            DefaultCategorySeed(
                id="income_investments_interest",
                name="Interest",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="income_investments_dividends",
                name="Dividends",
                sort_order=20,
            ),
        ),
    ),
    DefaultCategorySeed(
        id="income_other",
        name="Other income",
        sort_order=40,
        children=(
            DefaultCategorySeed(
                id="income_other_gifts",
                name="Gifts received",
                sort_order=10,
            ),
            DefaultCategorySeed(
                id="income_other_refunds",
                name="Refunds",
                sort_order=20,
            ),
        ),
    ),
)
