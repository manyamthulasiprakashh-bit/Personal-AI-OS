from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

import httpx

from app.config import Settings, get_settings
from app.schemas.stock import StockQuote


class StockProviderError(RuntimeError):
    """Raised when a stock provider cannot return a valid quote."""


class StockQuoteNotFoundError(StockProviderError):
    """Raised when a provider confirms that a symbol has no quote."""


class StockProvider(Protocol):
    def get_quote(self, symbol: str) -> StockQuote: ...


class UnavailableStockProvider:
    def __init__(self, message: str):
        self.message = message

    def get_quote(self, symbol: str) -> StockQuote:
        raise StockProviderError(self.message)


class MockStockProvider:
    _quotes = {
        "AAPL": (100.0, 1.5, 1.52, 98.5),
        "MSFT": (200.0, -2.0, -0.99, 202.0),
    }

    def get_quote(self, symbol: str) -> StockQuote:
        quote = self._quotes.get(symbol)
        if quote is None:
            raise StockQuoteNotFoundError("stock quote not found")
        price, change, change_percent, previous_close = quote
        return StockQuote(
            symbol=symbol,
            company=None,
            price=price,
            change=change,
            change_percent=change_percent,
            previous_close=previous_close,
            timestamp=None,
            data_source="mock",
            market_data_status="unknown",
        )


class AlphaVantageStockProvider:
    def __init__(self, settings: Settings | None = None, client=None):
        self.settings = settings or get_settings()
        self.client = client or httpx.Client()

    def get_quote(self, symbol: str) -> StockQuote:
        if not self.settings.alphavantage_api_key.strip():
            raise StockProviderError("stock provider is not configured")

        try:
            response = self.client.get(
                self.settings.alphavantage_api_base_url,
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": self.settings.alphavantage_api_key,
                },
                timeout=float(self.settings.stock_timeout_seconds),
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as error:
            raise StockProviderError("stock provider timed out") from error
        except httpx.HTTPStatusError as error:
            raise StockProviderError("stock provider request failed") from error
        except httpx.RequestError as error:
            raise StockProviderError("stock provider is unavailable") from error
        except (ValueError, TypeError) as error:
            raise StockProviderError("stock provider returned invalid data") from error

        if not isinstance(payload, dict):
            raise StockProviderError("stock provider returned invalid data")
        if payload.get("Information") or payload.get("Note") or payload.get("Error Message"):
            raise StockProviderError("stock provider request was rejected")

        raw_quote = payload.get("Global Quote")
        if not isinstance(raw_quote, dict) or not raw_quote:
            raise StockQuoteNotFoundError("stock quote not found")

        try:
            price = self._number(raw_quote, "05. price", required=True)
            change = self._number(raw_quote, "09. change")
            change_percent = self._percent(raw_quote.get("10. change percent"))
            previous_close = self._number(raw_quote, "08. previous close")
            timestamp = self._timestamp(raw_quote.get("07. latest trading day"))
            response_symbol = str(raw_quote.get("01. symbol", symbol)).strip().upper()
            if not response_symbol:
                raise ValueError
            return StockQuote(
                symbol=response_symbol,
                company=None,
                price=price,
                change=change,
                change_percent=change_percent,
                previous_close=previous_close,
                timestamp=timestamp,
                data_source="alphavantage",
                market_data_status="end_of_day",
            )
        except (ValueError, TypeError):
            raise StockProviderError("stock provider returned malformed quote") from None

    @staticmethod
    def _number(payload: dict, key: str, required: bool = False) -> float | None:
        value = payload.get(key)
        if value in (None, ""):
            if required:
                raise ValueError
            return None
        number = float(str(value).replace(",", "").strip())
        if number != number or number in (float("inf"), float("-inf")):
            raise ValueError
        return number

    @staticmethod
    def _percent(value) -> float | None:
        if value in (None, ""):
            return None
        return AlphaVantageStockProvider._number({"value": str(value).rstrip("%")}, "value")

    @staticmethod
    def _timestamp(value) -> datetime | None:
        if value in (None, ""):
            return None
        return datetime.strptime(str(value), "%Y-%m-%d").replace(tzinfo=timezone.utc)
