"""Capital Ethiopia news scraper."""
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from loguru import logger
from .base import BaseScraperImpl
from ...domain.entities import NewsArticle


class CapitalEthiopiaScraper(BaseScraperImpl):
    """Scraper for Capital Ethiopia news website."""
    
    def __init__(self):
        super().__init__(
            base_url="https://capitalethiopia.com",
            source_name="Capital Ethiopia"
        )
    
    async def fetch_latest_articles(self, limit: int = 10) -> List[NewsArticle]:
        """Fetch latest articles from Capital Ethiopia using pagination."""
        articles = []
        page = 1
        max_pages = 5  # Limit pages to scrape
        
        while len(articles) < limit and page <= max_pages:
            url = f"{self.base_url}/page/{page}/" if page > 1 else self.base_url
            html = await self.fetch_html(url)
            
            if not html:
                break
            
            try:
                soup = BeautifulSoup(html, "lxml")
                
                # Find article entries - Capital Ethiopia uses article tags
                article_tags = soup.find_all("article")
                
                if not article_tags:
                    # Try alternative selectors
                    article_tags = soup.find_all("div", class_="entry")
                
                for article_tag in article_tags:
                    try:
                        # Extract title from h2.entry-title
                        title_tag = article_tag.find("h2", class_="entry-title")
                        if not title_tag:
                            title_tag = article_tag.find("h2")
                        
                        if not title_tag:
                            continue
                        
                        link_tag = title_tag.find("a")
                        if not link_tag or not link_tag.get("href"):
                            continue
                        
                        article_url = link_tag["href"]
                        if not article_url.startswith("http"):
                            article_url = f"{self.base_url}{article_url}"
                        
                        title = link_tag.get_text(strip=True)
                        
                        # Extract date from time.entry-date
                        date_tag = article_tag.find("time", class_="entry-date")
                        if not date_tag:
                            date_tag = article_tag.find("time")
                        
                        published_date = datetime.now()
                        if date_tag:
                            date_str = date_tag.get("datetime") or date_tag.get_text(strip=True)
                            try:
                                published_date = date_parser.parse(date_str)
                            except Exception:
                                pass
                        
                        # Fetch full article
                        article_html = await self.fetch_html(article_url)
                        if article_html:
                            article = await self.parse(article_html, article_url)
                            article.published_date = published_date
                            articles.append(article)
                            
                            if len(articles) >= limit:
                                break
                    except Exception as e:
                        logger.debug(f"Failed to parse article: {e}")
                        continue
                
                # Check if there are more pages
                if not article_tags:
                    break
                
                page += 1
                
            except Exception as e:
                logger.error(f"Failed to parse Capital Ethiopia page {page}: {e}")
                break
        
        return articles[:limit]
    
    async def parse(self, raw_html: str, url: str) -> NewsArticle:
        """Parse HTML content into NewsArticle."""
        soup = BeautifulSoup(raw_html, "lxml")
        
        # Extract title
        title_tag = soup.find("h1", class_="entry-title") or soup.find("h1") or soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        
        # Extract content from div.entry-content
        content_div = soup.find("div", class_="entry-content")
        if not content_div:
            content_div = soup.find("article")
        
        content_parts = []
        if content_div:
            paragraphs = content_div.find_all("p")
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text:
                    content_parts.append(text)
        
        content = " ".join(content_parts) if content_parts else soup.get_text(strip=True)
        
        # Extract date
        date_tag = soup.find("time", class_="entry-date") or soup.find("time")
        published_date = datetime.now()
        
        if date_tag:
            date_str = date_tag.get("datetime") or date_tag.get_text(strip=True)
            try:
                published_date = date_parser.parse(date_str)
            except Exception:
                pass
        
        return NewsArticle(
            title=title,
            url=url,
            source=self.source_name,
            published_date=published_date,
            content=content
        )

