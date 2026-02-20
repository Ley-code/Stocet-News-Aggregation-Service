"""Market prices API routes."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, Path, Depends
from loguru import logger
from ..schemas.market_prices import (
    MarketPriceResponse,
    MarketPriceListResponse,
    MarketPriceHistoryResponse,
    TickerListResponse
)
from ..dependencies import get_get_market_prices_use_case
from ...use_cases.get_market_prices import GetMarketPricesUseCase


router = APIRouter(prefix="/api/v1/market-prices", tags=["market-prices"])


def market_price_to_response(price) -> MarketPriceResponse:
    """Convert domain entity to response model."""
    return MarketPriceResponse(
        ticker_symbol=price.ticker_symbol,
        price=price.price,
        timestamp=price.timestamp,
        source=price.source
    )


@router.get("", response_model=MarketPriceListResponse)
async def get_market_prices(
    get_market_prices_use_case: GetMarketPricesUseCase = Depends(get_get_market_prices_use_case)
) -> MarketPriceListResponse:
    """Get latest market prices for all tickers."""
    try:
        prices = await get_market_prices_use_case.get_latest_all()
        return MarketPriceListResponse(
            prices=[market_price_to_response(price) for price in prices],
            total=len(prices)
        )
    except Exception as e:
        logger.error(f"Failed to get market prices: {e}")
        raise


@router.get("/tickers", response_model=TickerListResponse)
async def get_tickers(
    get_market_prices_use_case: GetMarketPricesUseCase = Depends(get_get_market_prices_use_case)
) -> TickerListResponse:
    """Get list of all available ticker symbols."""
    try:
        tickers = await get_market_prices_use_case.get_all_tickers()
        return TickerListResponse(
            tickers=tickers,
            total=len(tickers)
        )
    except Exception as e:
        logger.error(f"Failed to get tickers: {e}")
        raise


@router.get("/{ticker}", response_model=MarketPriceResponse)
async def get_latest_price(
    ticker: str = Path(..., description="Ticker symbol (e.g., DASHEN, GADAA)"),
    get_market_prices_use_case: GetMarketPricesUseCase = Depends(get_get_market_prices_use_case)
) -> MarketPriceResponse:
    """Get latest price for a specific ticker."""
    try:
        price = await get_market_prices_use_case.get_latest_by_ticker(ticker.upper())
        if not price:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
        return market_price_to_response(price)
    except Exception as e:
        logger.error(f"Failed to get price for ticker {ticker}: {e}")
        raise


@router.get("/{ticker}/history", response_model=MarketPriceHistoryResponse)
async def get_price_history(
    ticker: str = Path(..., description="Ticker symbol (e.g., DASHEN, GADAA)"),
    start_date: Optional[datetime] = Query(None, description="Start date (ISO 8601 format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO 8601 format)"),
    get_market_prices_use_case: GetMarketPricesUseCase = Depends(get_get_market_prices_use_case)
) -> MarketPriceHistoryResponse:
    """Get historical prices for a ticker within a date range."""
    try:
        if not start_date or not end_date:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="Both start_date and end_date are required"
            )
        
        prices = await get_market_prices_use_case.get_by_ticker_and_date_range(
            ticker.upper(),
            start_date,
            end_date
        )
        
        return MarketPriceHistoryResponse(
            ticker_symbol=ticker.upper(),
            prices=[market_price_to_response(price) for price in prices],
            total=len(prices)
        )
    except Exception as e:
        logger.error(f"Failed to get price history for {ticker}: {e}")
        raise
