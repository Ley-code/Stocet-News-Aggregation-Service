"""PostgreSQL connection pool using asyncpg."""
from __future__ import annotations

import asyncpg
from loguru import logger
from ..config import settings

# Global connection pool
_pool: asyncpg.Pool | None = None


async def init_postgres() -> None:
    """Initialize the asyncpg connection pool."""
    global _pool
    if _pool is not None:
        return

    try:
        _pool = await asyncpg.create_pool(
            dsn=settings.postgres_dsn,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        print(f"Connected to PostgreSQL: {settings.postgres_dsn.split('@')[-1]}")
        logger.info(f"Connected to PostgreSQL: {settings.postgres_dsn.split('@')[-1]}")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        # Graceful degradation — don't crash the service
        _pool = None


async def close_postgres() -> None:
    """Close the asyncpg connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Closed PostgreSQL connection pool")


def get_pool() -> asyncpg.Pool | None:
    """Return the current connection pool (may be None if init failed)."""
    return _pool
