"""Generic RSS/Atom scraper used for most news sources.

RSS is far more stable than scraping each site's homepage markup, which is what broke the
original Addis Fortune scraper when the site changed its layout.
"""
import re
from datetime import datetime, timezone
from typing import List, Optional, Sequence
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from loguru import logger
from httpx import AsyncClient
from .base import BaseScraperImpl
from ...domain.entities import NewsArticle
from ...infrastructure.config import settings
from ...infrastructure.utils import sanitize_content, extract_image_url

_BODY_SELECTORS = [
    "div.entry-content", "div.td-post-content", "div.post-content", "div.article-content",
    "div.article-body", "div.single-content", "article", "main",
]
_FULL_TEXT_MIN = 600  # shorter than this and the feed only gave us a teaser


def _html_to_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "figure", "iframe"]):
        t.decompose()
    return sanitize_content(soup.get_text(" ", strip=True))


class RSSScraper(BaseScraperImpl):
    """Reads a feed and, when the feed carries only a teaser, fetches the article page for the body."""

    def __init__(
        self,
        source_name: str,
        feed_url: str,
        base_url: str,
        require_terms: Optional[Sequence[str]] = None,
        max_page_fetches: int = 6,
    ):
        super().__init__(base_url=base_url, source_name=source_name)
        self.feed_url = feed_url
        # For regional/global feeds: keep only items mentioning one of these words.
        self.require_terms = [t.lower() for t in (require_terms or [])]
        self.max_page_fetches = max_page_fetches
        self.request_delay = 1.0
        self.domestic = not self.require_terms

    async def connect(self) -> None:
        self.client = AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": settings.user_agent,
                "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
            },
            follow_redirects=True,
        )
        # robots.txt governs crawling article pages; the feed itself is meant for syndication.
        await self._load_robots_txt()

    async def _fetch_feed(self) -> Optional[str]:
        if not self.client:
            await self.connect()
        try:
            r = await self.client.get(self.feed_url)
            r.raise_for_status()
            return r.text
        except Exception as e:
            self._record_error()
            logger.error(f"{self.source_name}: failed to fetch feed {self.feed_url}: {e}")
            return None

    @staticmethod
    def _parse_date(raw: Optional[str]) -> datetime:
        if raw:
            try:
                d = date_parser.parse(raw)
                return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
            except Exception:
                pass
        return datetime.now(timezone.utc)

    @staticmethod
    def _feed_image(item) -> Optional[str]:
        for tag in item.find_all(["media:content", "media:thumbnail", "enclosure"]):
            url = tag.get("url")
            kind = (tag.get("type") or tag.get("medium") or "image").lower()
            if url and url.startswith("http") and "image" in kind:
                return url
        for html in (item.find("content:encoded"), item.find("description")):
            if html:
                img = BeautifulSoup(html.get_text(), "lxml").find("img")
                if img and img.get("src", "").startswith("http"):
                    return img["src"]
        return None

    def _matches_terms(self, text: str) -> bool:
        if not self.require_terms:
            return True
        low = text.lower()
        return any(re.search(rf"\b{re.escape(t)}\b", low) for t in self.require_terms)

    async def fetch_latest_articles(self, limit: int = 10) -> List[NewsArticle]:
        xml = await self._fetch_feed()
        if not xml:
            return []

        soup = BeautifulSoup(xml, "xml")
        items = soup.find_all("item") or soup.find_all("entry")
        articles: List[NewsArticle] = []
        page_fetches = 0

        for item in items:
            if len(articles) >= limit:
                break
            try:
                title_tag = item.find("title")
                title = title_tag.get_text(strip=True) if title_tag else ""
                link_tag = item.find("link")
                url = (link_tag.get("href") or link_tag.get_text(strip=True)) if link_tag else ""
                if not title or not url:
                    continue

                feed_html = ""
                for name in ("content:encoded", "content", "description", "summary"):
                    tag = item.find(name)
                    if tag and tag.get_text(strip=True):
                        feed_html = tag.get_text()
                        break
                content = _html_to_text(feed_html)
                summary = content[:300].rsplit(" ", 1)[0] + "…" if len(content) > 300 else content

                if not self._matches_terms(f"{title} {content}"):
                    continue
                if await self.already_stored(url):
                    continue

                image = self._feed_image(item)
                date_tag = item.find("pubDate") or item.find("published") or item.find("updated") or item.find("dc:date")
                published = self._parse_date(date_tag.get_text(strip=True) if date_tag else None)

                if len(content) < _FULL_TEXT_MIN and page_fetches < self.max_page_fetches:
                    page_fetches += 1
                    page_html = await self.fetch_html(url)
                    if page_html:
                        body, page_image = self._extract_body(page_html, url)
                        if len(body) > len(content):
                            content = body
                        image = image or page_image

                articles.append(
                    NewsArticle(
                        title=title,
                        url=url,
                        source=self.source_name,
                        published_date=published,
                        content=content or summary or title,
                        summary=summary or None,
                        image_url=image,
                    )
                )
            except Exception as e:
                logger.debug(f"{self.source_name}: skipped malformed feed item: {e}")

        return articles

    @staticmethod
    def _extract_body(html: str, url: str):
        soup = BeautifulSoup(html, "lxml")
        image = extract_image_url(soup, url)
        for t in soup(["script", "style", "nav", "footer", "aside", "form", "figure"]):
            t.decompose()
        best = ""
        for sel in _BODY_SELECTORS:
            node = soup.select_one(sel)
            if not node:
                continue
            text = sanitize_content(" ".join(p.get_text(" ", strip=True) for p in node.find_all("p")))
            if len(text) > len(best):
                best = text
            if len(best) >= _FULL_TEXT_MIN:
                break
        return best, image

    async def parse(self, raw_html: str, url: str) -> NewsArticle:
        body, image = self._extract_body(raw_html, url)
        soup = BeautifulSoup(raw_html, "lxml")
        h1 = soup.find("h1")
        return NewsArticle(
            title=h1.get_text(strip=True) if h1 else url,
            url=url,
            source=self.source_name,
            published_date=datetime.now(timezone.utc),
            content=body,
            image_url=image,
        )
