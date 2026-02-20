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
