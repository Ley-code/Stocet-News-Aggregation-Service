"""Domain interfaces - abstract base classes for adapters."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from .entities import NewsArticle


class BaseScraper(ABC):
    """Abstract base class for all news scrapers."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish session or browser context."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close session or browser context."""
        pass
    
    @abstractmethod
    async def fetch_latest_articles(self, limit: int = 10) -> List[NewsArticle]:
        """Retrieve the most recent articles.
        
        Args:
            limit: Maximum number of articles to fetch
            
        Returns:
            List of NewsArticle domain entities
        """
        pass
    
    @abstractmethod
    async def parse(self, raw_html: str, url: str) -> NewsArticle:
        """Convert HTML to Domain Entity.
        
        Args:
            raw_html: Raw HTML content
            url: Source URL of the article
            
        Returns:
            NewsArticle domain entity
        """
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of the news source."""
        pass


class NewsRepository(ABC):
    """Abstract base class for news article repositories."""
    
    @abstractmethod
    async def save(self, article: NewsArticle) -> None:
        """Save a news article to the repository."""
        pass
    
    @abstractmethod
    async def find_by_url(self, url: str) -> Optional[NewsArticle]:
        """Find an article by its URL."""
        pass
    
    @abstractmethod
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
        pass

