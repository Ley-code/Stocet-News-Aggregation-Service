"""Use case for harvesting market prices from ESX."""
from typing import List
from loguru import logger
from ..domain.entities import MarketPrice
from ..domain.interfaces import MarketPriceRepository
from ..adapters.scrapers.esx import ESXScraper
from .trigger_alerts import trigger_alerts


class HarvestMarketPricesUseCase:
    """Orchestrates the fetching of market prices from ESX."""
    
    def __init__(
        self,
        scraper: ESXScraper,
        repository: MarketPriceRepository
    ):
        """Initialize harvest market prices use case.
        
        Args:
            scraper: ESX scraper instance
            repository: Market price repository for persistence
        """
        self.scraper = scraper
        self.repository = repository
    
    async def execute(self) -> int:
        """Harvest market prices from ESX.
        
        Returns:
            Number of prices saved
        """
        total_saved = 0
        
        try:
            logger.info("Harvesting market prices from ESX...")
            
            # Connect to scraper
            await self.scraper.connect()
            
            # Fetch market prices
            prices = await self.scraper.fetch_market_prices()
            logger.info(f"Fetched {len(prices)} market prices from ESX")
            
            # Save all prices (historical storage)
            for price in prices:
                try:
                    was_saved = await self.repository.save(price)
                    if was_saved:
                        total_saved += 1
                        logger.debug(
                            f"Saved market price: {price.ticker_symbol} = {price.price}"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to save market price {price.ticker_symbol}: {e}",
                        exc_info=True
                    )
                    continue
            
            logger.info(
                f"Market price harvest complete: {total_saved} prices saved "
                f"out of {len(prices)} fetched"
            )
            
            # Trigger alert matching on the Core Service
            if total_saved > 0:
                trigger_alerts()
            
            # Disconnect from scraper
            await self.scraper.disconnect()
        
        except Exception as e:
            logger.error(f"Failed to harvest market prices from ESX: {e}", exc_info=True)
            try:
                await self.scraper.disconnect()
            except Exception:
                pass
        
        return total_saved

