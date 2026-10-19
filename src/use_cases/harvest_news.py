"""Use case for harvesting news from all sources."""
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List
from loguru import logger
from ..domain.entities import NewsArticle
from ..domain.interfaces import BaseScraper, NewsRepository
from ..infrastructure.nlp.keyword_extractor import KeywordExtractor
from .trigger_sentiment import trigger_sentiment

# Sources are independent, so scrape them in parallel (a few at a time) to keep one run short.
MAX_CONCURRENT_SOURCES = 4


@dataclass
class SourceResult:
    fetched: int = 0
    saved: int = 0
    duplicates: int = 0
    irrelevant: int = 0
    error: str = ""


class HarvestNewsUseCase:
    """Orchestrates the fetching of news from different sources."""

    def __init__(
        self,
        scrapers: List[BaseScraper],
        repository: NewsRepository,
        keyword_extractor: KeywordExtractor,
    ):
        self.scrapers = scrapers
        self.repository = repository
        self.keyword_extractor = keyword_extractor
        self.results: Dict[str, SourceResult] = {}

    async def _is_known(self, url: str) -> bool:
        return await self.repository.find_by_url(url) is not None

    def _classify(self, article: NewsArticle, domestic: bool = True) -> bool:
        """Tag the article and return whether it belongs in the feed."""
        text = f"{article.title} {article.content or ''}"
        categories = self.keyword_extractor.classify(article.title, article.content or "")
        article.tags = sorted(categories)
        if not article.summary and article.content:
            body = article.content.strip()
            article.summary = body[:300].rsplit(" ", 1)[0] + "…" if len(body) > 300 else body
        # ESX's own announcements are always relevant.
        if article.source == "ESX":
            return True
        return self.keyword_extractor.is_relevant(text, categories, domestic)

    async def _harvest_source(self, scraper: BaseScraper, limit: int, sem: asyncio.Semaphore) -> SourceResult:
        result = SourceResult()
        async with sem:
            try:
                logger.info(f"Harvesting from {scraper.source_name}...")
                if hasattr(scraper, "is_known"):
                    scraper.is_known = self._is_known
                await scraper.connect()
                articles = await scraper.fetch_latest_articles(limit=limit)
                result.fetched = len(articles)

                for article in articles:
                    try:
                        if not self._classify(article, getattr(scraper, "domestic", True)):
                            result.irrelevant += 1
                            continue
                        if await self.repository.save(article):
                            result.saved += 1
                        else:
                            result.duplicates += 1
                    except Exception as e:
                        logger.error(f"[{scraper.source_name}] failed to process '{article.title[:50]}': {e}")
                logger.info(
                    f"{scraper.source_name}: fetched={result.fetched} saved={result.saved} "
                    f"duplicates={result.duplicates} irrelevant={result.irrelevant}"
                )
            except Exception as e:
                result.error = str(e)
                logger.error(f"Failed to harvest from {scraper.source_name}: {e}")
            finally:
                try:
                    await scraper.disconnect()
                except Exception:
                    pass
        return result

    async def execute(self, limit_per_source: int = 10) -> int:
        """Harvest all sources; returns the number of new articles saved."""
        sem = asyncio.Semaphore(MAX_CONCURRENT_SOURCES)
        results = await asyncio.gather(*(self._harvest_source(s, limit_per_source, sem) for s in self.scrapers))
        self.results = {s.source_name: r for s, r in zip(self.scrapers, results)}

        total = sum(r.saved for r in results)
        failed = [name for name, r in self.results.items() if r.error]
        logger.info(f"Harvest complete: {total} new articles saved; sources failed: {failed or 'none'}")
        if total > 0:
            # Ask Core to classify the new articles now instead of waiting for its next scheduled pass.
            await asyncio.to_thread(trigger_sentiment)
        return total

    def summary(self) -> Dict[str, dict]:
        """Per-source counts, printed at the end of a run so it is easy to inspect in the job log."""
        return {name: r.__dict__ for name, r in self.results.items()}
