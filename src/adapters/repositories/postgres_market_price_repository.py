"""PostgreSQL repository implementation for market prices."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from loguru import logger
from ...domain.entities import MarketPrice
from ...domain.interfaces import MarketPriceRepository
from ...infrastructure.database.postgres_connection import get_pool


class PostgresMarketPriceRepository(MarketPriceRepository):
    """PostgreSQL implementation of MarketPriceRepository using asyncpg.

    Uses decimal.Decimal for NUMERIC column compatibility to prevent
    floating-point precision loss.
    """

    async def save(self, price: MarketPrice) -> bool:
        """Save a market price to PostgreSQL.

        Returns:
            True if price was saved, False otherwise
        """
        pool = get_pool()
        if pool is None:
            logger.warning("PostgreSQL pool not available, skipping market price save")
            return False

        try:
            await pool.execute(
                """
                INSERT INTO market_prices (ticker_symbol, price, percent_change, variation, timestamp, source)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                price.ticker_symbol,
                Decimal(str(price.price)),
                Decimal(str(price.percent_change)),
                Decimal(str(price.variation)),
                price.timestamp,
                price.source,
            )
            logger.debug(
                f"[PG] Saved market price: {price.ticker_symbol} = {price.price}"
            )
            return True
        except Exception as e:
            logger.error(
                f"[PG] Failed to save market price {price.ticker_symbol}: {e}"
            )
            raise

    async def find_latest_by_ticker(self, ticker: str) -> Optional[MarketPrice]:
        """Find the latest price for a specific ticker."""
        pool = get_pool()
        if pool is None:
            return None

        try:
            row = await pool.fetchrow(
                """
                SELECT * FROM market_prices
                WHERE ticker_symbol = $1
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                ticker.upper(),
            )
            if row:
                return self._row_to_domain(row)
            return None
        except Exception as e:
            logger.error(f"[PG] Failed to find latest price for {ticker}: {e}")
            return None

    async def find_by_ticker_and_date_range(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[MarketPrice]:
        """Find historical prices for a ticker within a date range."""
        pool = get_pool()
        if pool is None:
            return []

        try:
            rows = await pool.fetch(
                """
                SELECT * FROM market_prices
                WHERE ticker_symbol = $1 AND timestamp >= $2 AND timestamp <= $3
                ORDER BY timestamp ASC
                """,
                ticker.upper(),
                start_date,
                end_date,
            )
            return [self._row_to_domain(row) for row in rows]
        except Exception as e:
            logger.error(f"[PG] Failed to find historical prices for {ticker}: {e}")
            return []

    async def find_all_tickers(self) -> List[str]:
        """Get list of all available ticker symbols."""
        pool = get_pool()
        if pool is None:
            return []

        try:
            rows = await pool.fetch(
                "SELECT DISTINCT ticker_symbol FROM market_prices ORDER BY ticker_symbol"
            )
            return [row["ticker_symbol"] for row in rows]
        except Exception as e:
            logger.error(f"[PG] Failed to find all tickers: {e}")
            return []

    async def find_latest_all(self) -> List[MarketPrice]:
        """Get latest price for all tickers."""
        pool = get_pool()
        if pool is None:
            return []

        try:
            rows = await pool.fetch(
                """
                SELECT DISTINCT ON (ticker_symbol) *
                FROM market_prices
                ORDER BY ticker_symbol, timestamp DESC
                """
            )
            return [self._row_to_domain(row) for row in rows]
        except Exception as e:
            logger.error(f"[PG] Failed to find latest prices for all tickers: {e}")
            return []

    @staticmethod
    def _row_to_domain(row) -> MarketPrice:
        """Convert a database row to a domain entity."""
        return MarketPrice(
            ticker_symbol=row["ticker_symbol"],
            price=float(row["price"]),
            percent_change=float(row["percent_change"]),
            variation=float(row["variation"]),
            timestamp=row["timestamp"],
            source=row["source"],
        )
