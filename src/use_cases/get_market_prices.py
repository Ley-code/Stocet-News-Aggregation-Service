"""Use case for retrieving market prices."""
from datetime import datetime
from typing import List, Optional
from ..domain.entities import MarketPrice
from ..domain.interfaces import MarketPriceRepository


class GetMarketPricesUseCase:
    """Handles the logic for retrieving market prices via API."""
    
    def __init__(self, repository: MarketPriceRepository):
        """Initialize get market prices use case.
        
        Args:
            repository: Market price repository instance
        """
        self.repository = repository
    
    async def get_latest_all(self) -> List[MarketPrice]:
        """Get latest price for all tickers.
        
        Returns:
            List of latest market prices
        """
        return await self.repository.find_latest_all()
    
    async def get_latest_by_ticker(self, ticker: str) -> Optional[MarketPrice]:
        """Get latest price for a specific ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Latest market price or None if not found
        """
        return await self.repository.find_latest_by_ticker(ticker)
    
    async def get_by_ticker_and_date_range(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[MarketPrice]:
        """Get historical prices for a ticker within a date range.
        
        Args:
            ticker: Ticker symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            List of historical market prices
        """
        return await self.repository.find_by_ticker_and_date_range(
            ticker,
            start_date,
            end_date
        )
    
    async def get_all_tickers(self) -> List[str]:
        """Get list of all available ticker symbols.
        
        Returns:
            List of ticker symbols
        """
        return await self.repository.find_all_tickers()
    
    async def compute_indicators(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """Compute technical indicators for a ticker from historical prices.
        
        Currently computed on-the-fly from price history.
        Future: pre-compute on data insertion, store in DB, and fetch directly.
        
        Args:
            ticker: Ticker symbol
            start_date: Start date for data window
            end_date: End date for data window
            
        Returns:
            Dictionary with indicator values
        """
        prices_data = await self.repository.find_by_ticker_and_date_range(
            ticker, start_date, end_date
        )
        
        if not prices_data:
            return {
                "ticker_symbol": ticker,
                "period_days": (end_date - start_date).days,
                "data_points": 0,
            }
        
        # Extract closing prices (last price per day, sorted by timestamp)
        prices_data.sort(key=lambda p: p.timestamp)
        prices = [p.price for p in prices_data]
        
        result = {
            "ticker_symbol": ticker,
            "period_days": (end_date - start_date).days,
            "data_points": len(prices),
            "latest_price": prices[-1] if prices else None,
        }
        
        # Price change from first to last
        if len(prices) >= 2:
            result["price_change"] = round(prices[-1] - prices[0], 2)
            result["price_change_percent"] = round(
                ((prices[-1] - prices[0]) / prices[0]) * 100, 2
            ) if prices[0] != 0 else 0.0
        
        # SMA (20)
        if len(prices) >= 20:
            sma_window = prices[-20:]
            result["sma_20"] = round(sum(sma_window) / 20, 2)
        
        # EMA (20)
        if len(prices) >= 20:
            multiplier = 2 / (20 + 1)
            ema = sum(prices[:20]) / 20  # seed with SMA
            for price in prices[20:]:
                ema = (price - ema) * multiplier + ema
            result["ema_20"] = round(ema, 2)
        
        # RSI (14)
        if len(prices) >= 15:
            changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
            gains = [c for c in changes if c > 0]
            losses = [abs(c) for c in changes if c < 0]
            
            avg_gain = sum(gains) / 14 if gains else 0
            avg_loss = sum(losses) / 14 if losses else 0
            
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            result["rsi_14"] = round(rsi, 2)
            
            if rsi > 70:
                result["rsi_signal"] = "overbought"
            elif rsi < 30:
                result["rsi_signal"] = "oversold"
            else:
                result["rsi_signal"] = "neutral"
        
        return result

