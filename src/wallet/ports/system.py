from __future__ import annotations

from collections.abc import Callable
from datetime import date

CardIdGenerator = Callable[[], str]
DateProvider = Callable[[], date]
