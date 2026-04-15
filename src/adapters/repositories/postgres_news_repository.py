"""PostgreSQL repository implementation for news articles."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from loguru import logger
from ...domain.entities import NewsArticle
from ...domain.interfaces import NewsRepository
from ...infrastructure.database.postgres_connection import get_pool


class PostgresNewsRepository(NewsRepository):
    """PostgreSQL implementation of NewsRepository using asyncpg."""

    async def save(self, article: NewsArticle) -> bool:
        """Save a news article to PostgreSQL.

        Uses INSERT ... ON CONFLICT (url) DO NOTHING for idempotency.

        Returns:
            True if article was saved, False if it already exists
        """
        pool = get_pool()
        if pool is None:
            logger.warning("PostgreSQL pool not available, skipping article save")
            return False

        try:
            result = await pool.execute(
                """
                INSERT INTO articles (title, url, source, published_date, content, summary, tags, image_url)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (url) DO NOTHING
                """,
                article.title,
                article.url,
                article.source,
                article.published_date,
                article.content,
                article.summary,
                article.tags or [],
                article.image_url,
            )
            # asyncpg returns "INSERT 0 1" on success, "INSERT 0 0" on conflict
            was_inserted = result == "INSERT 0 1"
            if was_inserted:
                logger.debug(f"[PG] Saved article: {article.title[:50]}...")
            return was_inserted
        except Exception as e:
            logger.error(f"[PG] Failed to save article '{article.title[:50]}...': {e}")
            raise

    async def find_by_url(self, url: str) -> Optional[NewsArticle]:
        """Find an article by its URL."""
        pool = get_pool()
        if pool is None:
            return None

        try:
            row = await pool.fetchrow(
                "SELECT * FROM articles WHERE url = $1", url
            )
            if row:
                return self._row_to_domain(row)
            return None
        except Exception as e:
            logger.error(f"[PG] Failed to find article by URL {url}: {e}")
            return None

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
        """Find articles matching the given criteria."""
        pool = get_pool()
        if pool is None:
            return []

        try:
            conditions: list[str] = []
            params: list[object] = []
            idx = 1

            if category:
                conditions.append(f"${ idx } = ANY(tags)")
                params.append(category)
                idx += 1

            if source:
                conditions.append(f"source = ${idx}")
                params.append(source)
                idx += 1

            if start_date:
                conditions.append(f"published_date >= ${idx}")
                params.append(start_date)
                idx += 1

            if end_date:
                conditions.append(f"published_date <= ${idx}")
                params.append(end_date)
                idx += 1

            where = ""
            if conditions:
                where = "WHERE " + " AND ".join(conditions)

            query = f"""
                SELECT * FROM articles
                {where}
                ORDER BY published_date DESC
                LIMIT ${idx} OFFSET ${idx + 1}
            """
            params.extend([limit, skip])

            rows = await pool.fetch(query, *params)
            return [self._row_to_domain(row) for row in rows]
        except Exception as e:
            logger.error(f"[PG] Failed to find articles: {e}")
            return []

    @staticmethod
    def _row_to_domain(row) -> NewsArticle:
        """Convert a database row to a domain entity."""
        return NewsArticle(
            title=row["title"],
            url=row["url"],
            source=row["source"],
            published_date=row["published_date"],
            content=row["content"],
            summary=row["summary"],
            tags=list(row["tags"]) if row["tags"] else [],
            image_url=row["image_url"],
        )
