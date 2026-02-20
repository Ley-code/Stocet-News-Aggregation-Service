"""Domain entities for the news aggregation system."""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class NewsArticle:
    """Domain entity representing a news article."""
    
    title: str
    url: str
    source: str
    published_date: datetime
    content: str
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    image_url: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.tags is None:
            self.tags = []
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the article."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def has_tag(self, tag: str) -> bool:
        """Check if article has a specific tag."""
        return tag in self.tags


@dataclass
class MarketPrice:
    """Domain entity representing a market price for a stock ticker."""
    
    ticker_symbol: str
    price: float
    timestamp: datetime
    source: str = "ESX"

