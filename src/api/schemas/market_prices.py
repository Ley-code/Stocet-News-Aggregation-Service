"""Market prices API schemas."""
from datetime import datetime
from typing import List
from pydantic import BaseModel


class MarketPriceResponse(BaseModel):
    """Response model for market price."""
    
    ticker_symbol: str
    price: float
    percent_change: float
    variation: float
    timestamp: datetime
    source: str
    
    class Config:
        from_attributes = True


class MarketPriceListResponse(BaseModel):
    """Response model for list of market prices."""
    
    prices: List[MarketPriceResponse]
    total: int


class MarketPriceHistoryResponse(BaseModel):
    """Response model for historical market prices."""
    
    ticker_symbol: str
    prices: List[MarketPriceResponse]
    total: int


class TickerListResponse(BaseModel):
    """Response model for list of tickers."""
    
    tickers: List[str]
    total: int


class TechnicalIndicatorsResponse(BaseModel):
    """Response model for technical indicators.
    
    Currently computed on request from historical prices.
    Future: pre-computed on data insertion and fetched directly.
    """
    
    ticker_symbol: str
    period_days: int
    data_points: int
    sma_20: float | None = None
    ema_20: float | None = None
    rsi_14: float | None = None
    rsi_signal: str | None = None  # "overbought", "oversold", or "neutral"
    latest_price: float | None = None
    price_change: float | None = None
    price_change_percent: float | None = None
