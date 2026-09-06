from __future__ import annotations

import re

from app.providers.stock import StockProvider
from app.schemas.stock import StockQuote


class StockSymbolValidationError(ValueError):
    """Raised when a stock symbol is not accepted."""


class StockService:
    def __init__(self, provider: StockProvider):
        self.provider = provider

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()
        if not normalized or len(normalized) > 20 or not re.fullmatch(r"[A-Z0-9.-]+", normalized):
            raise StockSymbolValidationError("invalid stock symbol")
        return normalized

    def get_quote(self, symbol: str) -> StockQuote:
        return self.provider.get_quote(self.normalize_symbol(symbol))
