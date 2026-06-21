from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from wallet.domain._validation import normalize_nonblank
from wallet.domain.income_categories import (
    IncomeCategory,
    IncomeCategoryNotFoundError,
    normalize_category_name,
)
from wallet.infrastructure.memory import InMemoryIncomeCategoryRepository
from wallet.ports.income_categories import IncomeCategoryRepository
from wallet.ports.system import IncomeCategoryIdGenerator


class CreateIncomeCategoryRejectedError(ValueError):
    pass


class UpdateIncomeCategoryRejectedError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CreateIncomeCategory:
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
            _normalize_optional_value(self.category_id, field_name="income category id"),
        )
        object.__setattr__(
            self,
            "name",
            normalize_nonblank(self.name, field_name="income category name"),
        )
        object.__setattr__(
            self,
            "parent_id",
            _normalize_optional_value(self.parent_id, field_name="income category parent id"),
        )
        object.__setattr__(
            self,
            "icon",
            _normalize_optional_value(self.icon, field_name="income category icon"),
        )
        object.__setattr__(
            self,
            "color",
            _normalize_optional_value(self.color, field_name="income category color"),
        )


@dataclass(frozen=True, slots=True)
class UpdateIncomeCategory:
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
            normalize_nonblank(self.category_id, field_name="income category id"),
        )
        if self.name_provided:
            object.__setattr__(
                self,
                "name",
                normalize_nonblank(self.name or "", field_name="income category name"),
            )
        if self.parent_id_provided:
            object.__setattr__(
                self,
                "parent_id",
                _normalize_optional_value(self.parent_id, field_name="income category parent id"),
            )
        if self.icon_provided:
            object.__setattr__(
                self,
                "icon",
                _normalize_optional_value(self.icon, field_name="income category icon"),
            )
        if self.color_provided:
            object.__setattr__(
                self,
                "color",
                _normalize_optional_value(self.color, field_name="income category color"),
            )


@dataclass(frozen=True, slots=True)
class IncomeCategoryTreeNode:
    category: IncomeCategory
    children: tuple[IncomeCategoryTreeNode, ...] = ()


class IncomeCategoryService:
    def __init__(
        self,
        *,
        categories: IncomeCategoryRepository | None = None,
        generate_category_id: IncomeCategoryIdGenerator | None = None,
    ) -> None:
        self.categories = categories or InMemoryIncomeCategoryRepository()
        self._generate_category_id = generate_category_id or _new_income_category_id

    def create_income_category(self, command: CreateIncomeCategory) -> IncomeCategory:
        parent = self._resolve_parent(
            command.parent_id, error_cls=CreateIncomeCategoryRejectedError
        )
        category_id = command.category_id or self._generate_category_id()
        if self.categories.get(category_id) is not None:
            raise CreateIncomeCategoryRejectedError("category id already exists")
        self._assert_unique_sibling_name(
            normalized_name=normalize_category_name(command.name),
            parent_id=parent.id if parent is not None else None,
            error_cls=CreateIncomeCategoryRejectedError,
        )

        category = IncomeCategory.create(
            id=category_id,
            name=command.name,
            parent_id=parent.id if parent is not None else None,
            icon=command.icon,
            color=command.color,
            sort_order=command.sort_order,
        )
        self.categories.add(category)
        return category

    def update_income_category(self, command: UpdateIncomeCategory) -> IncomeCategory:
        category = self._require_category(command.category_id)

        name = command.name if command.name_provided and command.name is not None else category.name
        parent_id = category.parent_id
        if command.parent_id_provided:
            parent_id = command.parent_id
        icon = category.icon if not command.icon_provided else command.icon
        color = category.color if not command.color_provided else command.color
        sort_order = (
            command.sort_order
            if command.sort_order_provided and command.sort_order is not None
            else category.sort_order
        )

        parent = self._resolve_parent(
            parent_id,
            category_id=category.id,
            error_cls=UpdateIncomeCategoryRejectedError,
        )
        if parent is not None and self._has_children(category.id):
            raise UpdateIncomeCategoryRejectedError(
                "category with children cannot become a child category",
            )

        normalized_name = normalize_category_name(name)
        self._assert_unique_sibling_name(
            normalized_name=normalized_name,
            parent_id=parent.id if parent is not None else None,
            exclude_category_id=category.id,
            error_cls=UpdateIncomeCategoryRejectedError,
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

    def list_income_categories(self) -> list[IncomeCategoryTreeNode]:
        categories = self.categories.list()

        by_parent: dict[str | None, list[IncomeCategory]] = {}
        for category in categories:
            by_parent.setdefault(category.parent_id, []).append(category)

        for siblings in by_parent.values():
            siblings.sort(key=_category_sort_key)

        def build(parent_id: str | None) -> list[IncomeCategoryTreeNode]:
            return [
                IncomeCategoryTreeNode(
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
    ) -> IncomeCategory | None:
        if parent_id is None:
            return None
        if category_id is not None and parent_id == category_id:
            raise error_cls(
                "income category parent id must not equal category id",
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

    def _require_category(self, category_id: str) -> IncomeCategory:
        category = self.categories.get(category_id)
        if category is None:
            raise IncomeCategoryNotFoundError(category_id)
        return category


def _new_income_category_id() -> str:
    return f"income_category_{uuid4().hex}"


def _normalize_optional_value(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return normalize_nonblank(value, field_name=field_name)


def _category_sort_key(category: IncomeCategory) -> tuple[int, str]:
    return (category.sort_order, category.normalized_name)
