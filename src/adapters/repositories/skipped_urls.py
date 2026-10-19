"""Remembers article URLs we already looked at and decided are not relevant.

Without this, every harvest re-downloaded the same irrelevant articles (Capital Ethiopia alone: 15 page loads,
5 seconds apart) just to reject them again. The table is created on first use.
"""
from typing import Optional, Set
from loguru import logger
from ...infrastructure.database.postgres_connection import get_pool

# Entries older than this are forgotten, so a changed taxonomy gets another look at old URLs eventually.
REMEMBER_DAYS = 30


class SkippedUrlStore:
    def __init__(self) -> None:
        self._urls: Set[str] = set()

    async def load(self) -> int:
        """Create the table if needed and load recent skipped URLs into memory (one query per run)."""
        pool = get_pool()
        if pool is None:
            return 0
        try:
            await pool.execute(
                """
                CREATE TABLE IF NOT EXISTS skipped_articles (
                    url      text PRIMARY KEY,
                    source   text,
                    seen_at  timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            rows = await pool.fetch(
                "SELECT url FROM skipped_articles WHERE seen_at > now() - make_interval(days => $1)", REMEMBER_DAYS
            )
            self._urls = {r["url"] for r in rows}
            await pool.execute("DELETE FROM skipped_articles WHERE seen_at <= now() - make_interval(days => $1)", REMEMBER_DAYS)
        except Exception as e:  # never let the memory break a harvest
            logger.warning(f"Skipped-URL memory unavailable, continuing without it: {e}")
            self._urls = set()
        return len(self._urls)

    def is_skipped(self, url: str) -> bool:
        return url in self._urls

    async def mark(self, url: str, source: Optional[str] = None) -> None:
        if url in self._urls:
            return
        self._urls.add(url)
        pool = get_pool()
        if pool is None:
            return
        try:
            await pool.execute(
                "INSERT INTO skipped_articles (url, source) VALUES ($1, $2) ON CONFLICT (url) DO UPDATE SET seen_at = now()",
                url, source,
            )
        except Exception as e:
            logger.warning(f"Could not remember skipped URL {url}: {e}")
