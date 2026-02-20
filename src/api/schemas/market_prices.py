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
