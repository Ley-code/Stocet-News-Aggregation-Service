"""MongoDB repository implementation for market prices."""
from datetime import datetime
from typing import List, Optional
from loguru import logger
from ...domain.entities import MarketPrice
from ...domain.interfaces import MarketPriceRepository
from ...infrastructure.database.models import MarketPriceDocument


class MongoMarketPriceRepository(MarketPriceRepository):
    """MongoDB implementation of MarketPriceRepository."""
    
    async def save(self, price: MarketPrice) -> bool:
        """Save a market price to MongoDB.
        
        Returns:
            True if price was saved, False otherwise
        """
        try:
            # Create new document (historical storage - always save)
            document = MarketPriceDocument.from_domain(price)
            await document.insert()
            logger.debug(
                f"Saved market price: {price.ticker_symbol} = {price.price} "
                f"at {price.timestamp}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to save market price {price.ticker_symbol}: {e}",
                exc_info=True
            )
            raise
    
    async def find_latest_by_ticker(self, ticker: str) -> Optional[MarketPrice]:
        """Find the latest price for a specific ticker."""
        try:
            # Beanie: find() returns FindMany, use limit(1).to_list() to get first result
            documents = await MarketPriceDocument.find(
                MarketPriceDocument.ticker_symbol == ticker.upper()
            ).sort("-timestamp").limit(1).to_list()
            
            if documents and len(documents) > 0:
                return documents[0].to_domain()
            return None
        except Exception as e:
            logger.error(f"Failed to find latest price for ticker {ticker}: {e}")
            return None
    
    async def find_by_ticker_and_date_range(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[MarketPrice]:
        """Find historical prices for a ticker within a date range."""
        try:
            documents = await MarketPriceDocument.find(
                MarketPriceDocument.ticker_symbol == ticker.upper(),
                MarketPriceDocument.timestamp >= start_date,
                MarketPriceDocument.timestamp <= end_date
            ).sort("timestamp").to_list()
            
            return [doc.to_domain() for doc in documents]
        except Exception as e:
            logger.error(
                f"Failed to find historical prices for {ticker}: {e}"
            )
            return []
    
    async def find_all_tickers(self) -> List[str]:
        """Get list of all available ticker symbols."""
        try:
            # Use aggregation to get distinct ticker symbols
            pipeline = [
                {"$group": {"_id": "$ticker_symbol"}},
                {"$sort": {"_id": 1}}
            ]
            results = await MarketPriceDocument.aggregate(pipeline).to_list()
            return [result["_id"] for result in results]
        except Exception as e:
            logger.error(f"Failed to find all tickers: {e}")
            return []
    
    async def find_latest_all(self) -> List[MarketPrice]:
        """Get latest price for all tickers."""
        try:
            # Get all unique tickers first
            tickers = await self.find_all_tickers()
            
            # Get latest price for each ticker
            prices = []
            for ticker in tickers:
                latest = await self.find_latest_by_ticker(ticker)
                if latest:
                    prices.append(latest)
            
            # Sort by ticker symbol
            prices.sort(key=lambda p: p.ticker_symbol)
            return prices
        except Exception as e:
            logger.error(f"Failed to find latest prices for all tickers: {e}")
            return []
