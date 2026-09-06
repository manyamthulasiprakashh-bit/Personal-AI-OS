from fastapi.testclient import TestClient

from app.api.routes.stock import get_stock_provider
from app.main import app
from app.providers.stock import MockStockProvider, StockProviderError


def test_get_stock_quote_normalizes_symbol_and_returns_strict_quote():
    app.dependency_overrides[get_stock_provider] = lambda: MockStockProvider()
    try:
        response = TestClient(app).get("/api/stocks/ aapl ")
    finally:
        app.dependency_overrides.pop(get_stock_provider, None)

    assert response.status_code == 200
    assert response.json()["symbol"] == "AAPL"
    assert response.json()["data_source"] == "mock"


def test_get_stock_quote_rejects_invalid_symbol():
    app.dependency_overrides[get_stock_provider] = lambda: MockStockProvider()
    try:
        response = TestClient(app).get("/api/stocks/AAPL%3Fx%3D1")
    finally:
        app.dependency_overrides.pop(get_stock_provider, None)

    assert response.status_code == 422
    assert response.json()["detail"] == "invalid stock symbol"


def test_get_stock_quote_returns_404_for_unsupported_symbol():
    app.dependency_overrides[get_stock_provider] = lambda: MockStockProvider()
    try:
        response = TestClient(app).get("/api/stocks/NOPE")
    finally:
        app.dependency_overrides.pop(get_stock_provider, None)

    assert response.status_code == 404
    assert response.json()["detail"] == "stock quote not found"


def test_get_stock_quote_sanitizes_provider_failure():
    class FailingProvider:
        def get_quote(self, symbol):
            raise StockProviderError("private provider URL and api key")

    app.dependency_overrides[get_stock_provider] = lambda: FailingProvider()
    try:
        response = TestClient(app).get("/api/stocks/AAPL")
    finally:
        app.dependency_overrides.pop(get_stock_provider, None)

    assert response.status_code == 503
    assert response.json() == {"detail": "stock quote is unavailable"}
