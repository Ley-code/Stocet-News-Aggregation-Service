"""Use case for harvesting news from all sources."""
from typing import List
from loguru import logger
from ..domain.entities import NewsArticle
from ..domain.interfaces import BaseScraper, NewsRepository
from ..infrastructure.nlp.keyword_extractor import KeywordExtractor


class HarvestNewsUseCase:
    """Orchestrates the fetching of news from different sources."""
    
    def __init__(
        self,
        scrapers: List[BaseScraper],
        repository: NewsRepository,
        keyword_extractor: KeywordExtractor
    ):
        """Initialize harvest use case.
        
        Args:
            scrapers: List of scraper instances
            repository: News repository for persistence
            keyword_extractor: Keyword extractor for filtering
        """
        self.scrapers = scrapers
        self.repository = repository
        self.keyword_extractor = keyword_extractor
    
    async def execute(self, limit_per_source: int = 10) -> int:
        """Harvest news from all sources.
        
        Args:
            limit_per_source: Maximum articles to fetch per source
            
        Returns:
            Number of new articles saved
        """
        total_saved = 0
        
        for scraper in self.scrapers:
            try:
                logger.info(f"Harvesting from {scraper.source_name}...")
                
                # Connect to scraper
                await scraper.connect()
                
                # Fetch articles
                articles = await scraper.fetch_latest_articles(limit=limit_per_source)
                logger.info(f"Fetched {len(articles)} articles from {scraper.source_name}")
                
                # Process each article
                for article in articles:
                    try:
                        # Extract keywords and categories
                        keywords = self.keyword_extractor.extract_keywords(
                            f"{article.title} {article.content}"
                        )
                        categories = self.keyword_extractor.extract_categories(
                            f"{article.title} {article.content}"
                        )
                        
                        # Add tags
                        article.tags = list(categories)
                        
                        # Check if article has financial relevance
                        if keywords or categories:
                            # Save to repository
                            await self.repository.save(article)
                            total_saved += 1
                            logger.debug(
                                f"Saved article: {article.title[:50]}... "
                                f"(tags: {', '.join(categories)})"
                            )
                        else:
                            logger.debug(f"Skipped non-financial article: {article.title[:50]}...")
                    
                    except Exception as e:
                        logger.error(f"Failed to process article: {e}")
                        continue
                
                # Disconnect from scraper
                await scraper.disconnect()
            
            except Exception as e:
                logger.error(f"Failed to harvest from {scraper.source_name}: {e}")
                try:
                    await scraper.disconnect()
                except Exception:
                    pass
                continue
        
        logger.info(f"Harvest complete: {total_saved} new articles saved")
        return total_saved

