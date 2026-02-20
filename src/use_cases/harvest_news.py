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
                articles_processed = 0
                articles_with_keywords = 0
                articles_duplicates = 0
                articles_no_keywords = 0
                
                for article in articles:
                    try:
                        articles_processed += 1
                        
                        # Check if article has content
                        if not article.content or len(article.content.strip()) < 50:
                            logger.warning(
                                f"⚠ Article has insufficient content: {article.title[:50]}... "
                                f"(content length: {len(article.content) if article.content else 0})"
                            )
                        
                        # Extract keywords and categories
                        text_to_analyze = f"{article.title} {article.content or ''}"
                        keywords = self.keyword_extractor.extract_keywords(text_to_analyze)
                        categories = self.keyword_extractor.extract_categories(text_to_analyze)
                        
                        # Add tags
                        article.tags = list(categories)
                        
                        # ESX news bypasses keyword filtering (save all)
                        if article.source == "ESX":
                            articles_with_keywords += 1
                            was_saved = await self.repository.save(article)
                            if was_saved:
                                total_saved += 1
                                logger.info(
                                    f"✓ Saved ESX article (no filtering): {article.title[:50]}... "
                                    f"(tags: {', '.join(categories) if categories else 'none'})"
                                )
                            else:
                                articles_duplicates += 1
                                logger.info(
                                    f"⊘ Skipped duplicate ESX article: {article.title[:50]}... "
                                    f"(URL: {article.url[:60]}...)"
                                )
                            continue
                        
                        # Check if article has financial relevance
                        if keywords or categories:
                            articles_with_keywords += 1
                            # Save to repository
                            was_saved = await self.repository.save(article)
                            if was_saved:
                                total_saved += 1
                                logger.info(
                                    f"✓ Saved new article: {article.title[:50]}... "
                                    f"(tags: {', '.join(categories) if categories else 'none'}, keywords: {len(keywords)})"
                                )
                            else:
                                articles_duplicates += 1
                                logger.info(
                                    f"⊘ Skipped duplicate: {article.title[:50]}... "
                                    f"(URL: {article.url[:60]}...)"
                                )
                        else:
                            articles_no_keywords += 1
                            logger.info(
                                f"⊘ Skipped non-financial article: {article.title[:50]}... "
                                f"(no keywords found)"
                            )
                    
                    except Exception as e:
                        logger.error(f"Failed to process article '{article.title[:50]}...': {e}", exc_info=True)
                        continue
                
                logger.info(
                    f"Processed {articles_processed} articles from {scraper.source_name}: "
                    f"{articles_with_keywords} with keywords, "
                    f"{articles_duplicates} duplicates, "
                    f"{articles_no_keywords} no keywords, "
                    f"{total_saved} saved"
                )
                
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

