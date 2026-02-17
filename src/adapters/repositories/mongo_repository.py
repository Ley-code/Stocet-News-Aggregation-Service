"""MongoDB repository implementation."""
from datetime import datetime
from typing import List, Optional
from loguru import logger
from ...domain.entities import NewsArticle
from ...domain.interfaces import NewsRepository
from ...infrastructure.database.models import NewsArticleDocument


class MongoNewsRepository(NewsRepository):
    """MongoDB implementation of NewsRepository."""
    
    async def save(self, article: NewsArticle) -> None:
        """Save a news article to MongoDB."""
        try:
            # Check if article already exists
            existing = await NewsArticleDocument.find_one(
                NewsArticleDocument.url == article.url
            )
            
            if existing:
                logger.debug(f"Article already exists: {article.url}")
                return
            
            # Create new document
            document = NewsArticleDocument.from_domain(article)
            await document.insert()
            logger.info(f"Saved article: {article.title[:50]}...")
        except Exception as e:
            logger.error(f"Failed to save article {article.url}: {e}")
            raise
    
    async def find_by_url(self, url: str) -> Optional[NewsArticle]:
        """Find an article by its URL."""
        try:
            document = await NewsArticleDocument.find_one(
                NewsArticleDocument.url == url
            )
            if document:
                return document.to_domain()
            return None
        except Exception as e:
            logger.error(f"Failed to find article by URL {url}: {e}")
            return None
    
    async def find_all(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_text: Optional[str] = None,
        limit: int = 10,
        skip: int = 0
    ) -> List[NewsArticle]:
        """Find articles matching the given criteria."""
        try:
            query = {}
            
            if category:
                query["tags"] = category
            
            if source:
                query["source"] = source
            
            if start_date or end_date:
                date_query = {}
                if start_date:
                    date_query["$gte"] = start_date
                if end_date:
                    date_query["$lte"] = end_date
                query["published_date"] = date_query
            
            # Build the query
            if search_text:
                # Use MongoDB text search - add $text operator to query
                query["$text"] = {"$search": search_text}
            
            find_query = NewsArticleDocument.find(query)
            
            # Apply sorting, skip, and limit
            documents = await find_query.sort("-published_date").skip(skip).limit(limit).to_list()
            
            # Convert to domain entities
            return [doc.to_domain() for doc in documents]
        except Exception as e:
            logger.error(f"Failed to find articles: {e}")
            return []

