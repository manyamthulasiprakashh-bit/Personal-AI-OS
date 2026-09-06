from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.providers.factory import get_stock_provider
from app.providers.stock import StockProvider, StockProviderError, StockQuoteNotFoundError
from app.schemas.stock import StockQuote
from app.services.stock_service import StockService, StockSymbolValidationError

router = APIRouter(prefix="/api", tags=["stocks"])


def get_stock_service(provider: StockProvider = Depends(get_stock_provider)) -> StockService:
    return StockService(provider)


@router.get("/stocks/{symbol}", response_model=StockQuote)
def get_stock_quote(symbol: str, service: StockService = Depends(get_stock_service)) -> StockQuote:
    try:
        return service.get_quote(symbol)
    except StockSymbolValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid stock symbol"
        ) from error
    except StockQuoteNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="stock quote not found"
        ) from error
    except StockProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="stock quote is unavailable",
        ) from error
