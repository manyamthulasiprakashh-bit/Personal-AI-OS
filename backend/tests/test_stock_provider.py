from datetime import datetime, timezone

import httpx
import pytest

from app.config import Settings
from app.providers.stock import (
    AlphaVantageStockProvider,
    MockStockProvider,
    StockProviderError,
    StockQuoteNotFoundError,
)
from app.schemas.stock import StockQuote
from app.services.stock_service import StockService, StockSymbolValidationError


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.test")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("upstream failure", request=request, response=response)

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error:
            raise self.error
        return self.response


def settings(api_key="test-key"):
    return Settings(
        environment="test",
        database_url="sqlite+pysqlite:///unused.db",
        alphavantage_api_key=api_key,
    )


def alpha_payload():
    return {
        "Global Quote": {
            "01. symbol": "AAPL",
            "05. price": "189.50",
            "07. latest trading day": "2026-09-04",
            "08. previous close": "188.00",
            "09. change": "1.50",
            "10. change percent": "0.80%",
        }
    }


def test_stock_quote_rejects_unknown_fields():
    with pytest.raises(ValueError):
        StockQuote(
            symbol="AAPL",
            company=None,
            price=1,
            change=None,
            change_percent=None,
            previous_close=None,
            timestamp=None,
            data_source="mock",
            market_data_status="unknown",
            api_key="secret",
        )


def test_mock_provider_is_deterministic_and_network_free():
    provider = MockStockProvider()

    first = provider.get_quote("AAPL")
    second = provider.get_quote("AAPL")

    assert first == second
    assert first.data_source == "mock"
    assert first.market_data_status == "unknown"


def test_mock_provider_rejects_unsupported_symbol():
    with pytest.raises(StockQuoteNotFoundError):
        MockStockProvider().get_quote("NOPE")


def test_service_normalizes_symbol_before_provider_call():
    provider = MockStockProvider()

    quote = StockService(provider).get_quote(" aapl ")

    assert quote.symbol == "AAPL"


@pytest.mark.parametrize("symbol", ["", "https://example.com", "AAPL?x=1", "!@#"])
def test_service_rejects_invalid_symbols(symbol):
    with pytest.raises(StockSymbolValidationError):
        StockService(MockStockProvider()).get_quote(symbol)


def test_alpha_vantage_provider_normalizes_global_quote():
    client = FakeClient(FakeResponse(alpha_payload()))
    provider = AlphaVantageStockProvider(settings(), client=client)

    quote = provider.get_quote("AAPL")

    assert quote == StockQuote(
        symbol="AAPL",
        company=None,
        price=189.5,
        change=1.5,
        change_percent=0.8,
        previous_close=188.0,
        timestamp=datetime(2026, 9, 4, tzinfo=timezone.utc),
        data_source="alphavantage",
        market_data_status="end_of_day",
    )
    assert client.calls[0][1]["params"]["function"] == "GLOBAL_QUOTE"
    assert client.calls[0][1]["params"]["apikey"] == "test-key"
    assert client.calls[0][1]["params"]["symbol"] == "AAPL"


def test_alpha_vantage_provider_rejects_missing_quote():
    provider = AlphaVantageStockProvider(settings(), client=FakeClient(FakeResponse({})))

    with pytest.raises(StockQuoteNotFoundError):
        provider.get_quote("AAPL")


@pytest.mark.parametrize(
    "payload",
    [{"Note": "rate limit"}, {"Error Message": "invalid"}, {"Global Quote": {"05. price": "bad"}}],
)
def test_alpha_vantage_provider_sanitizes_provider_errors(payload):
    provider = AlphaVantageStockProvider(settings(), client=FakeClient(FakeResponse(payload)))

    with pytest.raises(StockProviderError) as error:
        provider.get_quote("AAPL")

    assert "rate limit" not in str(error.value).lower()
    assert "invalid" not in str(error.value).lower()


def test_alpha_vantage_provider_handles_timeout_without_leaking_details():
    provider = AlphaVantageStockProvider(
        settings(), client=FakeClient(error=httpx.TimeoutException("secret timeout details"))
    )

    with pytest.raises(StockProviderError, match="timed out") as error:
        provider.get_quote("AAPL")

    assert "secret" not in str(error.value)


def test_alpha_vantage_provider_requires_credentials():
    provider = AlphaVantageStockProvider(settings(api_key=""), client=FakeClient())

    with pytest.raises(StockProviderError, match="not configured"):
        provider.get_quote("AAPL")
