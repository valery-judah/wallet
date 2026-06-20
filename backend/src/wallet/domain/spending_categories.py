from __future__ import annotations

from dataclasses import dataclass

from ._validation import normalize_nonblank


class SpendingCategoryNotFoundError(LookupError):
    pass


@dataclass(slots=True)
class SpendingCategory:
    id: str
    name: str
    normalized_name: str
    parent_id: str | None
    icon: str | None
    color: str | None
    sort_order: int

    def __post_init__(self) -> None:
        self.id = normalize_nonblank(self.id, field_name="category id")
        self.name = normalize_nonblank(self.name, field_name="category name")
        self.normalized_name = normalize_category_name(self.name)
        self.parent_id = _normalize_optional_token(self.parent_id, field_name="category parent id")
        self.icon = _normalize_optional_token(self.icon, field_name="category icon")
        self.color = _normalize_optional_token(self.color, field_name="category color")
        if self.id == self.parent_id:
            raise ValueError("category parent id must not equal category id")

    @classmethod
    def create(
        cls,
        *,
        id: str,
        name: str,
        parent_id: str | None,
        icon: str | None,
        color: str | None,
        sort_order: int,
    ) -> SpendingCategory:
        return cls(
            id=id,
            name=name,
            normalized_name=normalize_category_name(name),
            parent_id=parent_id,
            icon=icon,
            color=color,
            sort_order=sort_order,
        )

    def update(
        self,
        *,
        name: str,
        parent_id: str | None,
        icon: str | None,
        color: str | None,
        sort_order: int,
    ) -> None:
        self.name = normalize_nonblank(name, field_name="category name")
        self.normalized_name = normalize_category_name(self.name)
        self.parent_id = _normalize_optional_token(parent_id, field_name="category parent id")
        self.icon = _normalize_optional_token(icon, field_name="category icon")
        self.color = _normalize_optional_token(color, field_name="category color")
        self.sort_order = sort_order
        if self.id == self.parent_id:
            raise ValueError("category parent id must not equal category id")


def normalize_category_name(value: str) -> str:
    return normalize_nonblank(value, field_name="category name").casefold()


def _normalize_optional_token(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return normalize_nonblank(value, field_name=field_name)
