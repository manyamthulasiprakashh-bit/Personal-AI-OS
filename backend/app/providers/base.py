from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Any


class BaseProvider(ABC):
    @abstractmethod
    def generate_daily_review(
        self, progress: dict[str, Any], *, target_date: date
    ) -> dict[str, Any]:
        """Generate a structured review from deterministic daily progress."""
