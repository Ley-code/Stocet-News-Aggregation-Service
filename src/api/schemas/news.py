"""News API schemas."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class NewsArticleResponse(BaseModel):
    """Response model for news article."""
    
    title: str
    url: str
    source: str
    published_date: datetime
    content: str
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class NewsListResponse(BaseModel):
    """Response model for news list."""
    
    articles: List[NewsArticleResponse]
    total: int
    limit: int
    skip: int

