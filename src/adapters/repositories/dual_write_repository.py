"""Dual-write repository wrappers.

These wrappers implement the strangler fig pattern: writes go to both
MongoDB (primary) and PostgreSQL (secondary). Reads delegate to the
primary only. If the secondary write fails, the error is logged but
the primary write is not affected.
"""
from datetime import datetime
from typing import List, Optional
from loguru import logger
from ...domain.entities import NewsArticle, MarketPrice
from ...domain.interfaces import NewsRepository, MarketPriceRepository


class DualWriteNewsRepository(NewsRepository):
    """Wraps a primary and secondary NewsRepository for dual-write."""

    def __init__(self, primary: NewsRepository, secondary: NewsRepository):
        self._primary = primary
        self._secondary = secondary

    async def save(self, article: NewsArticle) -> bool:
        """Save to primary (Mongo) first, then secondary (Postgres).

        The primary write must succeed. If the secondary write fails,
        the error is logged and the primary result is still returned.
        """
        # Primary write — must succeed
        result = await self._primary.save(article)

        # Secondary write — best effort
        try:
            await self._secondary.save(article)
        except Exception as e:
            logger.warning(
                f"[DualWrite] Secondary save failed for article "
                f"'{article.title[:50]}...': {e}"
            )

        return result

    async def find_by_url(self, url: str) -> Optional[NewsArticle]:
        """Delegate reads to primary only."""
        return await self._primary.find_by_url(url)

    async def find_all(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_text: Optional[str] = None,
        limit: int = 10,
        skip: int = 0,
    ) -> List[NewsArticle]:
        """Delegate reads to primary only."""
        return await self._primary.find_all(
            category=category,
            source=source,
            start_date=start_date,
            end_date=end_date,
            search_text=search_text,
            limit=limit,
            skip=skip,
        )


class DualWriteMarketPriceRepository(MarketPriceRepository):
    """Wraps a primary and secondary MarketPriceRepository for dual-write."""

    def __init__(self, primary: MarketPriceRepository, secondary: MarketPriceRepository):
        self._primary = primary
        self._secondary = secondary

    async def save(self, price: MarketPrice) -> bool:
        """Save to primary (Mongo) first, then secondary (Postgres).

        The primary write must succeed. If the secondary write fails,
        the error is logged and the primary result is still returned.
        """
        # Primary write — must succeed
        result = await self._primary.save(price)

        # Secondary write — best effort
        try:
            await self._secondary.save(price)
        except Exception as e:
            logger.warning(
                f"[DualWrite] Secondary save failed for market price "
                f"'{price.ticker_symbol}': {e}"
            )

        return result

    async def find_latest_by_ticker(self, ticker: str) -> Optional[MarketPrice]:
        """Delegate reads to primary only."""
        return await self._primary.find_latest_by_ticker(ticker)

    async def find_by_ticker_and_date_range(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[MarketPrice]:
        """Delegate reads to primary only."""
        return await self._primary.find_by_ticker_and_date_range(
            ticker, start_date, end_date
        )

    async def find_all_tickers(self) -> List[str]:
        """Delegate reads to primary only."""
        return await self._primary.find_all_tickers()

    async def find_latest_all(self) -> List[MarketPrice]:
        """Delegate reads to primary only."""
        return await self._primary.find_latest_all()
