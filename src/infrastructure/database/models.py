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
            tags=article.tags or []
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
            tags=self.tags
        )

