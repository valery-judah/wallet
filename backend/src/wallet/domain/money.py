from __future__ import annotations

from dataclasses import dataclass

from ._validation import normalize_currency


class CurrencyMismatchError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Money:
    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "currency",
            normalize_currency(self.currency, field_name="currency"),
        )

    @classmethod
    def zero(cls, currency: str) -> Money:
        return cls(amount_minor=0, currency=currency)

    def add(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(
            amount_minor=self.amount_minor + other.amount_minor,
            currency=self.currency,
        )

    def subtract(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(
            amount_minor=self.amount_minor - other.amount_minor,
            currency=self.currency,
        )

    def _assert_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError("currency mismatch")
