"""News API routes."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query, Depends
from loguru import logger
from ..schemas.news import NewsArticleResponse, NewsListResponse
from ..dependencies import get_get_news_use_case
from ...use_cases.get_news import GetNewsUseCase
from ...domain.entities import NewsArticle


router = APIRouter(prefix="/api/v1/news", tags=["news"])


def news_article_to_response(article: NewsArticle) -> NewsArticleResponse:
    """Convert domain entity to response model."""
    return NewsArticleResponse(
        title=article.title,
        url=article.url,
        source=article.source,
        published_date=article.published_date,
        content=article.content,
        summary=article.summary,
        tags=article.tags or [],
        image_url=article.image_url
    )


@router.get("", response_model=NewsListResponse)
async def get_news(
    q: Optional[str] = Query(None, description="Full-text search query"),
    category: Optional[str] = Query(None, description="Filter by category (Treasury Bills, Capital Markets, Macroeconomics, Politics)"),
    source: Optional[str] = Query(None, description="Filter by source (Addis Fortune, Capital Ethiopia, Reuters)"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date (ISO 8601 format)"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date (ISO 8601 format)"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    get_news_use_case: GetNewsUseCase = Depends(get_get_news_use_case)
) -> NewsListResponse:
    """Get news articles with filtering and search.
    
    Example queries:
    - /api/v1/news?category=Treasury+Bills&limit=20
    - /api/v1/news?source=Reuters&start_date=2025-01-01T00:00:00
    - /api/v1/news?q=ESX&category=Capital+Markets
    """
    try:
        articles = await get_news_use_case.execute(
            category=category,
            source=source,
            start_date=start_date,
            end_date=end_date,
            search_text=q,
            limit=limit,
            skip=skip
        )
        
        return NewsListResponse(
            articles=[news_article_to_response(article) for article in articles],
            total=len(articles),
            limit=limit,
            skip=skip
        )
    except Exception as e:
        logger.error(f"Failed to get news: {e}")
        raise

