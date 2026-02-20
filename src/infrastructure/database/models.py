"""Beanie ODM models for MongoDB."""
from beanie import Document, Indexed
from pydantic import Field
from datetime import datetime
from typing import List, Optional


class NewsArticleDocument(Document):
    """MongoDB document model for news articles."""
    
    title: str
    url: Indexed(str, unique=True)
    source: str
    published_date: datetime = Field(index=True)
    content: str
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list, index=True)
    image_url: Optional[str] = None
    
    class Settings:
        name = "articles"
        indexes = [
            [("title", "text"), ("content", "text")],  # Compound text index
            "published_date",
            "tags",
            "source"
        ]
    
    @classmethod
    def from_domain(cls, article) -> "NewsArticleDocument":
        """Create document from domain entity."""
        return cls(
            title=article.title,
            url=article.url,
            source=article.source,
            published_date=article.published_date,
            content=article.content,
            summary=article.summary,
            tags=article.tags or [],
            image_url=article.image_url
        )
    
    def to_domain(self):
        """Convert document to domain entity."""
        from ...domain.entities import NewsArticle
        return NewsArticle(
            title=self.title,
            url=self.url,
            source=self.source,
            published_date=self.published_date,
            content=self.content,
            summary=self.summary,
            tags=self.tags,
            image_url=self.image_url
        )


class MarketPriceDocument(Document):
    """MongoDB document model for market prices."""
    
    ticker_symbol: Indexed(str, index=True)
    price: float
    percent_change: float
    variation: float
    timestamp: datetime = Field(index=True)
    source: str = "ESX"
    
    class Settings:
        name = "market_prices"
        indexes = [
            "ticker_symbol",
            "timestamp",
            [("ticker_symbol", 1), ("timestamp", -1)],  # Compound index: ticker_symbol ascending, timestamp descending
            "source"
        ]
    
    @classmethod
    def from_domain(cls, price) -> "MarketPriceDocument":
        """Create document from domain entity."""
        return cls(
            ticker_symbol=price.ticker_symbol,
            price=price.price,
            percent_change=price.percent_change,
            variation=price.variation,
            timestamp=price.timestamp,
            source=price.source
        )
    
    def to_domain(self):
        """Convert document to domain entity."""
        from ...domain.entities import MarketPrice
        return MarketPrice(
            ticker_symbol=self.ticker_symbol,
            price=self.price,
            percent_change=self.percent_change,
            variation=self.variation,
            timestamp=self.timestamp,
            source=self.source
        )

