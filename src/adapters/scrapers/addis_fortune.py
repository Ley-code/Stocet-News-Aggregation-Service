"""Addis Fortune news scraper."""
import re
from datetime import datetime
from typing import List, Optional
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from loguru import logger
from .base import BaseScraperImpl
from ...domain.entities import NewsArticle


class AddisFortuneScraper(BaseScraperImpl):
    """Scraper for Addis Fortune news website."""
    
    def __init__(self):
        super().__init__(
            base_url="https://addisfortune.news",
            source_name="Addis Fortune"
        )
    
    async def fetch_latest_articles(self, limit: int = 10) -> List[NewsArticle]:
        """Fetch latest articles from Addis Fortune homepage."""
        articles = []
        
        # Fetch homepage
        html = await self.fetch_html(self.base_url)
        if not html:
            return articles
        
        try:
            soup = BeautifulSoup(html, "lxml")
            
            # Find article containers - Addis Fortune uses Bootstrap grid classes
            article_containers = soup.find_all("div", class_=re.compile(r"col-md-\d+"))
            
            for container in article_containers[:limit * 2]:  # Get more to filter
                try:
                    # Find headline (h4 or h5)
                    headline_tag = container.find(["h4", "h5"])
                    if not headline_tag:
                        continue
                    
                    # Find link
                    link_tag = headline_tag.find("a")
                    if not link_tag or not link_tag.get("href"):
                        continue
                    
                    article_url = link_tag["href"]
                    if not article_url.startswith("http"):
                        article_url = f"{self.base_url}{article_url}"
                    
                    title = headline_tag.get_text(strip=True)
                    
                    # Find date - usually below headline
                    date_tag = container.find("time") or container.find(string=re.compile(r"\w+\s+\d+,\s+\d{4}"))
                    published_date = datetime.now()  # Default to now
                    
                    if date_tag:
                        if isinstance(date_tag, str):
                            date_text = date_tag.strip()
                        else:
                            date_text = date_tag.get_text(strip=True)
                        
                        try:
                            # Normalize date format (e.g., "Dec 6 , 2025" -> "Dec 6, 2025")
                            date_text = re.sub(r"\s+,\s+", ", ", date_text)
                            published_date = date_parser.parse(date_text)
                        except Exception as e:
                            logger.debug(f"Failed to parse date '{date_text}': {e}")
                    
                    # Find summary/description
                    summary_tag = container.find("p")
                    summary = summary_tag.get_text(strip=True) if summary_tag else None
                    
                    # Fetch full article content
                    article_html = await self.fetch_html(article_url)
                    if article_html:
                        article = await self.parse(article_html, article_url)
                        article.published_date = published_date
                        if summary:
                            article.summary = summary
                        articles.append(article)
                        
                        if len(articles) >= limit:
                            break
                except Exception as e:
                    logger.debug(f"Failed to parse article container: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Failed to parse Addis Fortune homepage: {e}")
        
        return articles
    
    async def parse(self, raw_html: str, url: str) -> NewsArticle:
        """Parse HTML content into NewsArticle."""
        soup = BeautifulSoup(raw_html, "lxml")
        
        # Extract title
        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        
        # Extract content - look for main article content
        content_divs = soup.find_all("div", class_=re.compile(r"entry-content|article-content|post-content"))
        if not content_divs:
            # Fallback: get all paragraphs
            content_divs = soup.find_all("article")
        
        content_parts = []
        for div in content_divs:
            paragraphs = div.find_all("p")
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text:
                    content_parts.append(text)
        
        content = " ".join(content_parts) if content_parts else soup.get_text(strip=True)
        
        # Extract date if available
        date_tag = soup.find("time") or soup.find(string=re.compile(r"\w+\s+\d+,\s+\d{4}"))
        published_date = datetime.now()
        
        if date_tag:
            if isinstance(date_tag, str):
                date_text = date_tag.strip()
            else:
                date_text = date_tag.get_text(strip=True)
            
            try:
                date_text = re.sub(r"\s+,\s+", ", ", date_text)
                published_date = date_parser.parse(date_text)
            except Exception:
                pass
        
        return NewsArticle(
            title=title,
            url=url,
            source=self.source_name,
            published_date=published_date,
            content=content
        )

