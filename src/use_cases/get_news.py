"""Use case for retrieving news articles."""
from datetime import datetime
from typing import List, Optional
from ..domain.entities import NewsArticle
from ..domain.interfaces import NewsRepository


class GetNewsUseCase:
    """Handles the logic for retrieving news articles via API."""
    
    def __init__(self, repository: NewsRepository):
        """Initialize get news use case.
        
        Args:
            repository: News repository instance
        """
        self.repository = repository
    
    async def execute(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search_text: Optional[str] = None,
        limit: int = 10,
        skip: int = 0
    ) -> List[NewsArticle]:
        """Retrieve news articles matching criteria.
        
        Args:
            category: Filter by category tag
            source: Filter by news source
            start_date: Filter by start date
            end_date: Filter by end date
            search_text: Full-text search query
            limit: Maximum number of results
            skip: Number of results to skip (pagination)
            
        Returns:
            List of matching news articles
        """
        return await self.repository.find_all(
            category=category,
            source=source,
            start_date=start_date,
            end_date=end_date,
            search_text=search_text,
            limit=limit,
            skip=skip
        )

