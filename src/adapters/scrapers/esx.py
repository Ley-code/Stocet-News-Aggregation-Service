"""ESX (Ethiopian Securities Exchange) scraper."""
import asyncio
import re
from datetime import datetime
from typing import List, Optional
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from loguru import logger
from .base import BaseScraperImpl
from ...domain.entities import NewsArticle, MarketPrice


class ESXScraper(BaseScraperImpl):
    """Scraper for Ethiopian Securities Exchange (ESX) website."""
    
    def __init__(self):
        super().__init__(
            base_url="https://esx.et",
            source_name="ESX"
        )
    
    _BROWSER_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    async def fetch_market_prices(self) -> List[MarketPrice]:
        """Fetch live prices from ESX's ticker.

        ESX's homepage loads its ticker through a WordPress AJAX call (action ``esx_get_ticker``) that needs
        the page's public nonce. We read the nonce from the homepage and make the same call. If that
        fails (layout change), fall back to the old JSON endpoint.
        """
        # ESX's server is slow and occasionally times out, so retry before falling back.
        for attempt in range(1, 4):
            try:
                prices = await self._fetch_market_prices_ajax()
                if prices:
                    return prices
                logger.warning("ESX AJAX ticker returned no prices")
                break
            except Exception as e:
                logger.error(f"ESX AJAX ticker attempt {attempt}/3 failed: {e!r}")
                if attempt < 3:
                    await asyncio.sleep(2 * attempt)
        return await self._fetch_market_prices_legacy()

    async def _fetch_market_prices_ajax(self) -> List[MarketPrice]:
        if not self.client:
            await self.connect()
        headers = {"User-Agent": self._BROWSER_UA}

        home = await self.client.get(self.base_url + "/", headers=headers, timeout=30.0)
        home.raise_for_status()
        nonce_match = re.search(r"const\s+nonce\s*=\s*[\"']([A-Za-z0-9]+)[\"']", home.text)
        ajax_match = re.search(r"const\s+ajaxUrl\s*=\s*[\"']([^\"']+)[\"']", home.text)
        if not nonce_match:
            raise ValueError("ticker nonce not found on ESX homepage")
        ajax_url = ajax_match.group(1) if ajax_match else self.base_url + "/wp-admin/admin-ajax.php"

        response = await self.client.post(
            ajax_url,
            data={"action": "esx_get_ticker", "nonce": nonce_match.group(1)},
            headers={**headers, "Accept": "application/json"},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success"):
            raise ValueError(f"ESX ticker returned success=false: {str(payload)[:200]}")

        now = datetime.now()
        prices: List[MarketPrice] = []
        for item in payload.get("data") or []:
            try:
                symbol = (item.get("symbol") or "").strip().upper()
                price = float(str(item.get("price")).replace(",", ""))
                pct = float(item.get("change") or 0)
            except (ValueError, TypeError):
                continue
            if not symbol:
                continue
            # The ticker gives only the % change; derive the absolute move from it.
            previous = price / (1 + pct / 100) if pct > -100 else price
            prices.append(
                MarketPrice(
                    ticker_symbol=symbol,
                    price=price,
                    percent_change=pct,
                    variation=round(price - previous, 4),
                    timestamp=now,
                    source="ESX",
                )
            )
        logger.info(f"Found {len(prices)} market prices from ESX ticker: {[p.ticker_symbol for p in prices]}")
        return prices

    async def _fetch_market_prices_legacy(self) -> List[MarketPrice]:
        """Old JSON endpoint (/wp-json/custom/v1/ticker). It started returning 404; kept only as a fallback.
        
        Returns:
            List of MarketPrice entities
        """
        prices = []
        
        # ESX provides a direct API endpoint for market prices
        api_url = "https://esx.et/wp-json/custom/v1/ticker"
        
        try:
            # Ensure we have a client connection
            if not self.client:
                await self.connect()
            
            # Fetch data from API
            response = await self.client.get(
                api_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Accept": "application/json"
                },
                timeout=10.0
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Process each market price item
            for item in data:
                try:
                    security_code = item.get("SECURITY_CODE")
                    price_value = item.get("PRICE")
                    percent_change_value = item.get("PERCENT_CHANGE", 0)
                    variation_value = item.get("VARIATION", 0)
                    
                    if not security_code or price_value is None:
                        continue
                    
                    # Convert price to float
                    try:
                        price = float(price_value)
                    except (ValueError, TypeError):
                        logger.debug(f"Could not parse price '{price_value}' for {security_code}")
                        continue
                    
                    # Convert percent_change to float (default to 0 if missing or invalid)
                    try:
                        percent_change = float(percent_change_value) if percent_change_value is not None else 0.0
                    except (ValueError, TypeError):
                        logger.debug(f"Could not parse percent_change '{percent_change_value}' for {security_code}, using 0")
                        percent_change = 0.0
                    
                    # Convert variation to float (default to 0 if missing or invalid)
                    try:
                        variation = float(variation_value) if variation_value is not None else 0.0
                    except (ValueError, TypeError):
                        logger.debug(f"Could not parse variation '{variation_value}' for {security_code}, using 0")
                        variation = 0.0
                    
                    # Create MarketPrice entity
                    prices.append(MarketPrice(
                        ticker_symbol=security_code.upper(),
                        price=price,
                        percent_change=percent_change,
                        variation=variation,
                        timestamp=datetime.now(),
                        source="ESX"
                    ))
                    
                    logger.debug(f"Extracted price: {security_code} = {price}, change: {percent_change}%, variation: {variation}")
                    
                except Exception as e:
                    logger.debug(f"Failed to process market price item: {e}")
                    continue
            
            if prices:
                logger.info(f"Found {len(prices)} market prices from ESX API: {[p.ticker_symbol for p in prices]}")
            else:
                logger.warning("No market prices extracted from ESX API")
            
        except Exception as e:
            logger.error(f"Failed to fetch ESX market prices from API: {e}", exc_info=True)
        
        return prices
    
    async def fetch_latest_articles(self, limit: int = 10) -> List[NewsArticle]:
        """Fetch latest articles from ESX news page."""
        articles = []
        
        # Fetch news page
        url = f"{self.base_url}/news-and-resources/latest-news/"
        html = await self.fetch_html(url)
        if not html:
            return articles
        
        try:
            soup = BeautifulSoup(html, "lxml")
            
            # ESX uses Elementor structure - find the posts container
            posts_container = soup.find("div", class_=re.compile(r"elementor-posts-container", re.I))
            
            if not posts_container:
                # Fallback: look for article elements directly
                article_containers = soup.find_all("article", class_=re.compile(r"elementor-post", re.I))
            else:
                # Find all article elements with class "elementor-post"
                article_containers = posts_container.find_all("article", class_=re.compile(r"elementor-post", re.I))
            
            # If still no articles, try finding any article elements
            if not article_containers:
                article_containers = soup.find_all("article")
            
            logger.info(f"Found {len(article_containers)} article containers on ESX news page")
            
            for container in article_containers[:limit * 2]:  # Get more to filter
                try:
                    # Find title in h3.elementor-post_title
                    title_tag = container.find("h3", class_=re.compile(r"elementor-post_title", re.I))
                    if not title_tag:
                        # Fallback to any h3, h2, or h4
                        title_tag = container.find("h3") or container.find("h2") or container.find("h4")
                    
                    if not title_tag:
                        logger.debug("No title tag found in article container")
                        continue
                    
                    # Find link - could be in title tag or thumbnail link
                    link_tag = title_tag.find("a")
                    if not link_tag:
                        # Try thumbnail link
                        link_tag = container.find("a", class_=re.compile(r"elementor-post_thumbnail_link", re.I))
                    
                    if not link_tag or not link_tag.get("href"):
                        logger.debug("No link found in article container")
                        continue
                    
                    article_url = link_tag["href"]
                    if not article_url.startswith("http"):
                        article_url = f"{self.base_url}{article_url}"
                    
                    # Extract title
                    title = link_tag.get_text(strip=True) or title_tag.get_text(strip=True)
                    if not title:
                        logger.debug(f"No title text found for article: {article_url}")
                        continue
                    
                    # Extract date from elementor-post-date
                    date_span = container.find("span", class_=re.compile(r"elementor-post-date", re.I))
                    published_date = datetime.now()
                    
                    if date_span:
                        date_text = date_span.get_text(strip=True)
                        try:
                            published_date = date_parser.parse(date_text)
                        except Exception:
                            logger.debug(f"Could not parse date '{date_text}', using current date")
                    else:
                        # Fallback: look for time tag or date string
                        date_tag = container.find("time")
                        if date_tag:
                            date_text = date_tag.get("datetime") or date_tag.get_text(strip=True)
                            try:
                                published_date = date_parser.parse(date_text)
                            except Exception:
                                pass
                    
                    logger.debug(f"Processing ESX article: {title[:50]}... ({article_url})")
                    
                    # Fetch full article
                    article_html = await self.fetch_html(article_url)
                    if article_html:
                        article = await self.parse(article_html, article_url)
                        article.published_date = published_date
                        articles.append(article)
                        logger.info(f"✓ Successfully parsed ESX article: {title[:50]}...")
                        
                        if len(articles) >= limit:
                            break
                    else:
                        logger.warning(f"Could not fetch article content from: {article_url}")
                except Exception as e:
                    logger.debug(f"Failed to parse ESX article container: {e}", exc_info=True)
                    continue
            
            logger.info(f"Successfully fetched {len(articles)} articles from ESX")
        
        except Exception as e:
            logger.error(f"Failed to parse ESX news page: {e}", exc_info=True)
        
        return articles[:limit]
    
    async def parse(self, raw_html: str, url: str) -> NewsArticle:
        """Parse HTML content into NewsArticle."""
        soup = BeautifulSoup(raw_html, "lxml")
        
        # Extract title - ESX uses h1 for article titles
        title_tag = soup.find("h1", class_=re.compile(r"entry-title|post-title|article-title", re.I))
        if not title_tag:
            title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else "No Title"
        
        # Extract content - ESX uses Elementor, look for elementor-widget-text-editor or entry-content
        content_parts = []
        
        # Try Elementor text editor widgets first
        text_editors = soup.find_all("div", class_=re.compile(r"elementor-widget-text-editor", re.I))
        for editor in text_editors:
            paragraphs = editor.find_all("p")
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 20:  # Filter out very short text
                    content_parts.append(text)
        
        # If no Elementor content, try standard WordPress/Elementor content divs
        if not content_parts:
            content_divs = soup.find_all("div", class_=re.compile(r"entry-content|elementor-post__content|post-content|article-content", re.I))
            for div in content_divs:
                paragraphs = div.find_all("p")
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        content_parts.append(text)
        
        # Fallback: look for article tag
        if not content_parts:
            article_tag = soup.find("article")
            if article_tag:
                paragraphs = article_tag.find_all("p")
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        content_parts.append(text)
        
        # Final fallback: get all paragraphs from body
        if not content_parts:
            paragraphs = soup.find_all("p")
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 50:  # Only longer paragraphs
                    content_parts.append(text)
        
        content = " ".join(content_parts) if content_parts else soup.get_text(strip=True)
        
        # Sanitize content
        from ...infrastructure.utils import sanitize_content, extract_image_url
        sanitized_content = sanitize_content(content)
        
        # Extract image URL
        image_url = extract_image_url(soup, url)
        
        # Extract date - ESX might use time tag or date span
        date_tag = soup.find("time")
        if not date_tag:
            date_tag = soup.find("span", class_=re.compile(r"post-date|entry-date|published", re.I))
        
        published_date = datetime.now()
        if date_tag:
            if isinstance(date_tag, str):
                date_text = date_tag.strip()
            else:
                date_text = date_tag.get("datetime") or date_tag.get_text(strip=True)
            
            try:
                published_date = date_parser.parse(date_text)
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
