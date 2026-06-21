from __future__ import annotations

from collections.abc import Callable
from datetime import date

AccountIdGenerator = Callable[[], str]
DateProvider = Callable[[], date]
IncomeCategoryIdGenerator = Callable[[], str]
PostingIdGenerator = Callable[[], str]
SpendingCategoryIdGenerator = Callable[[], str]
TransactionIdGenerator = Callable[[], str]
