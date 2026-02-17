"""Reuters news scraper using Playwright for dynamic content."""
from datetime import datetime
from typing import List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import stealth_async
from loguru import logger
from ...domain.entities import NewsArticle
from ...domain.interfaces import BaseScraper
from ...infrastructure.config import settings


class ReutersScraper(BaseScraper):
    """Scraper for Reuters using Playwright to bypass Cloudflare."""
    
    def __init__(self):
        self._source_name = "Reuters"
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    @property
    def source_name(self) -> str:
        """Return the name of the news source."""
        return self._source_name
    
    async def connect(self) -> None:
        """Launch Playwright browser with stealth mode."""
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            self.context = await self.browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Inject stealth scripts
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)
            
            self.page = await self.context.new_page()
            await stealth_async(self.page)
            
            logger.info("Connected to Reuters via Playwright")
        except Exception as e:
            logger.error(f"Failed to connect to Reuters: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Playwright browser."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            logger.info("Disconnected from Reuters")
        except Exception as e:
            logger.error(f"Error disconnecting from Reuters: {e}")
    
    async def fetch_latest_articles(self, limit: int = 10) -> List[NewsArticle]:
        """Fetch latest articles from Reuters Africa section."""
        articles = []
        
        if not self.page:
            await self.connect()
        
        try:
            # Navigate to Reuters Africa section
            url = "https://www.reuters.com/world/africa/"
            logger.info(f"Navigating to {url}")
            await self.page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for content to load
            await self.page.wait_for_selector("article", timeout=10000)
            
            # Extract article links
            article_links = await self.page.evaluate("""
                () => {
                    const articles = Array.from(document.querySelectorAll('article a[href*="/world/"]'));
                    return articles.slice(0, 20).map(a => a.href).filter((v, i, a) => a.indexOf(v) === i);
                }
            """)
            
            logger.info(f"Found {len(article_links)} article links")
            
            for article_url in article_links[:limit]:
                try:
                    article = await self._fetch_article(article_url)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.error(f"Failed to fetch article {article_url}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Failed to fetch Reuters articles: {e}")
        
        return articles
    
    async def _fetch_article(self, url: str) -> Optional[NewsArticle]:
        """Fetch a single article from Reuters."""
        if not self.page:
            return None
        
        try:
            await self.page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait for article content
            await self.page.wait_for_selector("article", timeout=10000)
            
            # Extract article data using JavaScript
            article_data = await self.page.evaluate("""
                () => {
                    const article = document.querySelector('article');
                    if (!article) return null;
                    
                    const titleEl = article.querySelector('h1') || document.querySelector('h1');
                    const title = titleEl ? titleEl.innerText.trim() : '';
                    
                    const dateEl = article.querySelector('time') || document.querySelector('[datetime]');
                    const dateStr = dateEl ? (dateEl.getAttribute('datetime') || dateEl.innerText) : '';
                    
                    const contentEls = article.querySelectorAll('p');
                    const content = Array.from(contentEls)
                        .map(p => p.innerText.trim())
                        .filter(t => t.length > 0)
                        .join('\\n\\n');
                    
                    return {
                        title: title,
                        date: dateStr,
                        content: content
                    };
                }
            """)
            
            if not article_data or not article_data.get("title"):
                return None
            
            # Parse date
            published_date = datetime.now()
            if article_data.get("date"):
                try:
                    from dateutil import parser as date_parser
                    published_date = date_parser.parse(article_data["date"])
                except Exception:
                    pass
            
            return NewsArticle(
                title=article_data["title"],
                url=url,
                source=self.source_name,
                published_date=published_date,
                content=article_data.get("content", "")
            )
        
        except Exception as e:
            logger.error(f"Failed to parse Reuters article {url}: {e}")
            return None
    
    async def parse(self, raw_html: str, url: str) -> NewsArticle:
        """Parse HTML content - not used for Playwright-based scraper."""
        # This method is not used for Playwright scraper
        # Articles are parsed directly in _fetch_article
        raise NotImplementedError("Reuters scraper uses Playwright, not HTML parsing")

