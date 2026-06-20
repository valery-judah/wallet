from __future__ import annotations

from collections.abc import Callable
from datetime import date

AccountIdGenerator = Callable[[], str]
DateProvider = Callable[[], date]
