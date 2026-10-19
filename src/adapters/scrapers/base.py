"""Base scraper implementation with common functionality."""
import asyncio
import time
from typing import Awaitable, Callable, List, Optional
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
from loguru import logger
from httpx import AsyncClient
from ...domain.entities import NewsArticle
from ...domain.interfaces import BaseScraper
from ...infrastructure.config import settings


class BaseScraperImpl(BaseScraper):
    """Base implementation with common scraper functionality."""
    
    def __init__(self, base_url: str, source_name: str):
        """Initialize base scraper.
        
        Args:
            base_url: Base URL of the news source
            source_name: Name of the news source
        """
        self.base_url = base_url
        self._source_name = source_name
        self.client: Optional[AsyncClient] = None
        self.robots_parser: Optional[RobotFileParser] = None
        self.last_request_time: float = 0
        self.error_count: int = 0
        self.circuit_breaker_active: bool = False
        self.circuit_breaker_until: float = 0
        # Seconds between requests; subclasses may lower this for polite, low-volume sources.
        self.request_delay: Optional[float] = None
        # Local Ethiopian outlets: any recognised topic is relevant. Regional feeds must also mention Ethiopia.
        self.domestic: bool = True
        # Injected by the harvest use case: True if the URL is already stored, so we skip fetching it.
        self.is_known: Optional[Callable[[str], Awaitable[bool]]] = None
    
    @property
    def source_name(self) -> str:
        """Return the name of the news source."""
        return self._source_name
    
    async def connect(self) -> None:
        """Establish HTTP client session."""
        self.client = AsyncClient(
            timeout=30.0,
            headers={"User-Agent": settings.user_agent},
            follow_redirects=True
        )
        await self._load_robots_txt()
        logger.info(f"Connected to {self.source_name}")
    
    async def disconnect(self) -> None:
        """Close HTTP client session."""
        if self.client:
            await self.client.aclose()
            self.client = None
        logger.info(f"Disconnected from {self.source_name}")
    
    async def _load_robots_txt(self) -> None:
        """Load and parse robots.txt file."""
        try:
            robots_url = urljoin(self.base_url, "/robots.txt")
            if self.client:
                response = await self.client.get(robots_url)
                if response.status_code == 200:
                    self.robots_parser = RobotFileParser()
                    self.robots_parser.set_url(robots_url)
                    self.robots_parser.read()
                    logger.info(f"Loaded robots.txt for {self.source_name}")
        except Exception as e:
            logger.warning(f"Failed to load robots.txt for {self.source_name}: {e}")
            self.robots_parser = None
    
    def _can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt."""
        if not self.robots_parser:
            return True  # If robots.txt not available, allow access
        
        user_agent = settings.user_agent.split("/")[0]  # Extract bot name
        return self.robots_parser.can_fetch(user_agent, url)
    
    async def _rate_limit(self) -> None:
        """Implement rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        delay = self.request_delay if self.request_delay is not None else settings.rate_limit_delay
        
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is active.
        
        Returns:
            True if requests should be blocked
        """
        if not self.circuit_breaker_active:
            return False
        
        if time.time() >= self.circuit_breaker_until:
            # Circuit breaker timeout expired
            self.circuit_breaker_active = False
            self.error_count = 0
            logger.info(f"Circuit breaker reset for {self.source_name}")
            return False
        
        return True
    
    def _record_error(self) -> None:
        """Record an error and activate circuit breaker if threshold reached."""
        self.error_count += 1
        if self.error_count >= settings.circuit_breaker_threshold:
            self.circuit_breaker_active = True
            self.circuit_breaker_until = time.time() + settings.circuit_breaker_timeout
            logger.warning(
                f"Circuit breaker activated for {self.source_name} "
                f"for {settings.circuit_breaker_timeout} seconds"
            )
    
    def _record_success(self) -> None:
        """Record a successful request."""
        self.error_count = 0
    
    async def already_stored(self, url: str) -> bool:
        """Check the repository (when wired) so we never download pages we already have."""
        if self.is_known is None:
            return False
        try:
            return await self.is_known(url)
        except Exception as e:
            logger.debug(f"is_known check failed for {url}: {e}")
            return False

    async def fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL with rate limiting and error handling.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content or None if fetch failed
        """
        if await self._check_circuit_breaker():
            logger.warning(f"Circuit breaker active for {self.source_name}, skipping request")
            return None
        
        if not self._can_fetch(url):
            logger.warning(f"robots.txt disallows fetching {url}")
            return None
        
        await self._rate_limit()
        
        if not self.client:
            await self.connect()
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            self._record_success()
            return response.text
        except Exception as e:
            self._record_error()
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    async def fetch_latest_articles(self, limit: int = 10) -> List[NewsArticle]:
        """Retrieve the most recent articles - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement fetch_latest_articles")
    
    async def parse(self, raw_html: str, url: str) -> NewsArticle:
        """Convert HTML to Domain Entity - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement parse")

