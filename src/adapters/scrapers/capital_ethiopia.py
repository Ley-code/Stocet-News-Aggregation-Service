"""Capital Ethiopia news scraper."""
from datetime import datetime
from typing import List
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from loguru import logger
from .base import BaseScraperImpl
from ...domain.entities import NewsArticle


class CapitalEthiopiaScraper(BaseScraperImpl):
    """Scraper for Capital Ethiopia news website.
    
    Capital Ethiopia (capitalethiopia.com) uses the Flavor theme (td-module pattern).
    Homepage structure:
        - No <article> tags
        - Articles in divs with td-module-* classes
        - Titles in <h3 class="entry-title"> containing <a href="...">
        - Dates in <time class="entry-date">
    
    Article page structure:
        - Title in <h1 class="tdb-title-text"> or first <h1>
        - Content in <div class="td-post-content"> (NOT entry-content)
        - Date in <time class="entry-date">
    """
    
    def __init__(self):
        super().__init__(
            base_url="https://capitalethiopia.com",
            source_name="Capital Ethiopia"
        )
    
    async def fetch_latest_articles(self, limit: int = 10) -> List[NewsArticle]:
        """Fetch latest articles from Capital Ethiopia."""
        articles = []
        page = 1
        max_pages = 3
        
        while len(articles) < limit and page <= max_pages:
            url = f"{self.base_url}/page/{page}/" if page > 1 else self.base_url
            html = await self.fetch_html(url)
            
            if not html:
                logger.warning(f"Capital Ethiopia: No HTML returned for {url}")
                break
            
            try:
                soup = BeautifulSoup(html, "html.parser")
                
                # Capital Ethiopia uses <h3 class="entry-title"> for article titles
                title_tags = soup.find_all("h3", class_="entry-title")
                
                if not title_tags:
                    # Fallback: try h2
                    title_tags = soup.find_all("h2", class_="entry-title")
                
                if not title_tags:
                    logger.warning(f"Capital Ethiopia: No title tags found on page {page}")
                    break
                
                logger.info(f"Capital Ethiopia: Found {len(title_tags)} title tags on page {page}")
                
                fresh_on_page = 0  # articles on this listing page we hadn't already stored or rejected
                for title_tag in title_tags:
                    try:
                        link_tag = title_tag.find("a")
                        if not link_tag or not link_tag.get("href"):
                            continue
                        
                        article_url = link_tag["href"]
                        if not article_url.startswith("http"):
                            article_url = f"{self.base_url}{article_url}"
                        
                        title = link_tag.get_text(strip=True)
                        if not title:
                            continue
                        
                        # Extract date from nearby <time> tag
                        # Walk up to find the module container, then look for time
                        parent = title_tag.parent
                        date_tag = None
                        for _ in range(4):  # Walk up a few levels
                            if parent is None:
                                break
                            date_tag = parent.find("time", class_="entry-date")
                            if date_tag:
                                break
                            date_tag = parent.find("time")
                            if date_tag:
                                break
                            parent = parent.parent
                        
                        published_date = datetime.now()
                        if date_tag:
                            date_str = date_tag.get("datetime") or date_tag.get_text(strip=True)
                            try:
                                published_date = date_parser.parse(date_str)
                            except Exception:
                                pass
                        
                        if await self.already_stored(article_url):
                            continue
                        fresh_on_page += 1

                        # Fetch full article
                        article_html = await self.fetch_html(article_url)
                        if article_html:
                            article = await self.parse(article_html, article_url)
                            article.published_date = published_date
                            articles.append(article)
                            logger.debug(f"Capital Ethiopia: Scraped article: {title[:60]}")
                            
                            if len(articles) >= limit:
                                break
                    except Exception as e:
                        logger.debug(f"Capital Ethiopia: Failed to parse article: {e}")
                        continue
                
                if not title_tags:
                    break

                # Newest first: a page with nothing new means every later page is old news too.
                if fresh_on_page == 0:
                    break

                page += 1
                
            except Exception as e:
                logger.error(f"Failed to parse Capital Ethiopia page {page}: {e}")
                break
        
        logger.info(f"Capital Ethiopia: Scraped {len(articles)} articles total")
        return articles[:limit]
    
    async def parse(self, raw_html: str, url: str) -> NewsArticle:
        """Parse article page HTML into NewsArticle."""
        soup = BeautifulSoup(raw_html, "html.parser")
        
        # Extract title — Capital Ethiopia uses tdb-title-text or just h1
        title_tag = (
            soup.find("h1", class_="tdb-title-text")
            or soup.find("h1", class_="entry-title")
            or soup.find("h1")
            or soup.find("title")
        )
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        
        # Extract content — Capital Ethiopia uses td-post-content (NOT entry-content)
        content_div = (
            soup.find("div", class_="td-post-content")
            or soup.find("div", class_="tdb-block-inner td-fix-index")
            or soup.find("div", class_="entry-content")
            or soup.find("article")
        )
        
        content_parts = []
        if content_div:
            paragraphs = content_div.find_all("p")
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text:
                    content_parts.append(text)
        
        content = " ".join(content_parts) if content_parts else soup.get_text(strip=True)
        
        # Sanitize content
        from ...infrastructure.utils import sanitize_content, extract_image_url
        sanitized_content = sanitize_content(content)
        
        # Extract image URL
        image_url = extract_image_url(soup, url)
        
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
            content=sanitized_content,
            image_url=image_url
        )
