from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from wallet.domain._validation import normalize_nonblank
from wallet.domain.spending_categories import (
    SpendingCategory,
    SpendingCategoryNotFoundError,
    normalize_category_name,
)
from wallet.infrastructure.memory import InMemorySpendingCategoryRepository
from wallet.ports.spending_categories import SpendingCategoryRepository
from wallet.ports.system import SpendingCategoryIdGenerator


class CreateSpendingCategoryRejectedError(ValueError):
    pass


class UpdateSpendingCategoryRejectedError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CreateSpendingCategory:
    name: str
    category_id: str | None = None
    parent_id: str | None = None
    icon: str | None = None
    color: str | None = None
    sort_order: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "category_id",
            _normalize_optional_value(self.category_id, field_name="category id"),
        )
        object.__setattr__(
            self,
            "name",
            normalize_nonblank(self.name, field_name="category name"),
        )
        object.__setattr__(
            self,
            "parent_id",
            _normalize_optional_value(self.parent_id, field_name="category parent id"),
        )
        object.__setattr__(
            self,
            "icon",
            _normalize_optional_value(self.icon, field_name="category icon"),
        )
        object.__setattr__(
            self,
            "color",
            _normalize_optional_value(self.color, field_name="category color"),
        )


@dataclass(frozen=True, slots=True)
class UpdateSpendingCategory:
    category_id: str
    name: str | None = None
    name_provided: bool = False
    parent_id: str | None = None
    parent_id_provided: bool = False
    icon: str | None = None
    icon_provided: bool = False
    color: str | None = None
    color_provided: bool = False
    sort_order: int | None = None
    sort_order_provided: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "category_id",
            normalize_nonblank(self.category_id, field_name="category id"),
        )
        if self.name_provided:
            object.__setattr__(
                self,
                "name",
                normalize_nonblank(self.name or "", field_name="category name"),
            )
        if self.parent_id_provided:
            object.__setattr__(
                self,
                "parent_id",
                _normalize_optional_value(self.parent_id, field_name="category parent id"),
            )
        if self.icon_provided:
            object.__setattr__(
                self,
                "icon",
                _normalize_optional_value(self.icon, field_name="category icon"),
            )
        if self.color_provided:
            object.__setattr__(
                self,
                "color",
                _normalize_optional_value(self.color, field_name="category color"),
            )


@dataclass(frozen=True, slots=True)
class SpendingCategoryTreeNode:
    category: SpendingCategory
    children: tuple[SpendingCategoryTreeNode, ...] = ()


class SpendingCategoryService:
    def __init__(
        self,
        *,
        categories: SpendingCategoryRepository | None = None,
        generate_category_id: SpendingCategoryIdGenerator | None = None,
    ) -> None:
        self.categories = categories or InMemorySpendingCategoryRepository()
        self._generate_category_id = generate_category_id or _new_spending_category_id

    def create_spending_category(self, command: CreateSpendingCategory) -> SpendingCategory:
        parent = self._resolve_parent(
            command.parent_id,
            error_cls=CreateSpendingCategoryRejectedError,
        )
        category_id = command.category_id or self._generate_category_id()
        if self.categories.get(category_id) is not None:
            raise CreateSpendingCategoryRejectedError("category id already exists")
        self._assert_unique_sibling_name(
            normalized_name=normalize_category_name(command.name),
            parent_id=parent.id if parent is not None else None,
            error_cls=CreateSpendingCategoryRejectedError,
        )

        category = SpendingCategory.create(
            id=category_id,
            name=command.name,
            parent_id=parent.id if parent is not None else None,
            icon=command.icon,
            color=command.color,
            sort_order=command.sort_order,
        )
        self.categories.add(category)
        return category

    def update_spending_category(self, command: UpdateSpendingCategory) -> SpendingCategory:
        category = self._require_category(command.category_id)

        name = category.name
        if command.name_provided:
            name = command.name or category.name

        parent_id = category.parent_id
        if command.parent_id_provided:
            parent_id = command.parent_id

        icon = category.icon
        if command.icon_provided:
            icon = command.icon

        color = category.color
        if command.color_provided:
            color = command.color

        sort_order = category.sort_order
        if command.sort_order_provided and command.sort_order is not None:
            sort_order = command.sort_order

        parent = self._resolve_parent(
            parent_id,
            category_id=category.id,
            error_cls=UpdateSpendingCategoryRejectedError,
        )
        if parent is not None and self._has_children(category.id):
            raise UpdateSpendingCategoryRejectedError(
                "category with children cannot become a child category",
            )

        normalized_name = normalize_category_name(name)
        self._assert_unique_sibling_name(
            normalized_name=normalized_name,
            parent_id=parent.id if parent is not None else None,
            exclude_category_id=category.id,
            error_cls=UpdateSpendingCategoryRejectedError,
        )

        category.update(
            name=name,
            parent_id=parent.id if parent is not None else None,
            icon=icon,
            color=color,
            sort_order=sort_order,
        )
        self.categories.save(category)
        return category

    def list_spending_categories(self) -> list[SpendingCategoryTreeNode]:
        categories = self.categories.list()

        by_parent: dict[str | None, list[SpendingCategory]] = {}
        for category in categories:
            by_parent.setdefault(category.parent_id, []).append(category)

        for siblings in by_parent.values():
            siblings.sort(key=_category_sort_key)

        def build(parent_id: str | None) -> list[SpendingCategoryTreeNode]:
            return [
                SpendingCategoryTreeNode(
                    category=category,
                    children=tuple(build(category.id)),
                )
                for category in by_parent.get(parent_id, [])
            ]

        return build(None)

    def _resolve_parent(
        self,
        parent_id: str | None,
        *,
        category_id: str | None = None,
        error_cls: type[ValueError],
    ) -> SpendingCategory | None:
        if parent_id is None:
            return None
        if category_id is not None and parent_id == category_id:
            raise error_cls(
                "category parent id must not equal category id",
            )
        parent = self._require_category(parent_id)
        if parent.parent_id is not None:
            raise error_cls(
                "category hierarchy supports only two levels",
            )
        return parent

    def _assert_unique_sibling_name(
        self,
        *,
        normalized_name: str,
        parent_id: str | None,
        error_cls: type[ValueError],
        exclude_category_id: str | None = None,
    ) -> None:
        for category in self.categories.list():
            if exclude_category_id is not None and category.id == exclude_category_id:
                continue
            if category.parent_id != parent_id:
                continue
            if category.normalized_name == normalized_name:
                raise error_cls(
                    "category name must be unique within its sibling group",
                )

    def _has_children(self, category_id: str) -> bool:
        return any(category.parent_id == category_id for category in self.categories.list())

    def _require_category(self, category_id: str) -> SpendingCategory:
        category = self.categories.get(category_id)
        if category is None:
            raise SpendingCategoryNotFoundError(category_id)
        return category


def _new_spending_category_id() -> str:
    return f"spending_category_{uuid4().hex}"


def _normalize_optional_value(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return normalize_nonblank(value, field_name=field_name)


def _category_sort_key(category: SpendingCategory) -> tuple[int, str]:
    return (category.sort_order, category.normalized_name)
