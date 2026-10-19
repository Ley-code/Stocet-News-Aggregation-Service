"""FastAPI dependency injection."""
from functools import lru_cache
from ..adapters.scrapers.esx import ESXScraper
from ..adapters.scrapers.registry import build_news_scrapers
from ..infrastructure.config import settings
from ..adapters.repositories.postgres_news_repository import PostgresNewsRepository
from ..adapters.repositories.skipped_urls import SkippedUrlStore
from ..adapters.repositories.postgres_market_price_repository import PostgresMarketPriceRepository
from ..adapters.repositories.dual_write_repository import (
    DualWriteNewsRepository,
    DualWriteMarketPriceRepository,
)
from ..infrastructure.nlp.keyword_extractor import KeywordExtractor
from ..use_cases.harvest_news import HarvestNewsUseCase
from ..use_cases.harvest_market_prices import HarvestMarketPricesUseCase
from ..use_cases.get_news import GetNewsUseCase
from ..use_cases.get_market_prices import GetMarketPricesUseCase
from ..use_cases.filter_news import FilterNewsUseCase


# Set by the app lifespan: True only if MongoDB connected on this run. While False, writes go to PostgreSQL only.
_mongo_ready = False


def set_mongo_ready(ready: bool) -> None:
    global _mongo_ready
    _mongo_ready = ready


def _mirror_to_mongo() -> bool:
    return settings.mongo_enabled and _mongo_ready


@lru_cache()
def get_keyword_extractor() -> KeywordExtractor:
    """Get keyword extractor instance."""
    return KeywordExtractor()


@lru_cache()
def get_mongo_news_repository():
    """MongoDB news repository. Imported lazily so Motor/Beanie aren't loaded unless Mongo is enabled."""
    from ..adapters.repositories.mongo_repository import MongoNewsRepository
    return MongoNewsRepository()


@lru_cache()
def get_mongo_market_price_repository():
    """MongoDB market price repository (lazy import, see above)."""
    from ..adapters.repositories.market_price_repository import MongoMarketPriceRepository
    return MongoMarketPriceRepository()


@lru_cache()
def get_postgres_news_repository() -> PostgresNewsRepository:
    """Get PostgreSQL news repository instance."""
    return PostgresNewsRepository()


@lru_cache()
def get_postgres_market_price_repository() -> PostgresMarketPriceRepository:
    """Get PostgreSQL market price repository instance."""
    return PostgresMarketPriceRepository()


def get_repository():
    """Articles go to PostgreSQL (source of truth, also used for duplicate checks) and are mirrored to MongoDB."""
    if not _mirror_to_mongo():
        return get_postgres_news_repository()
    return DualWriteNewsRepository(
        primary=get_postgres_news_repository(),
        secondary=get_mongo_news_repository(),
    )


def get_market_price_repository():
    """Prices go to PostgreSQL (source of truth) and are mirrored to MongoDB."""
    if not _mirror_to_mongo():
        return get_postgres_market_price_repository()
    return DualWriteMarketPriceRepository(
        primary=get_postgres_market_price_repository(),
        secondary=get_mongo_market_price_repository(),
    )


def get_harvest_news_use_case() -> HarvestNewsUseCase:
    """Get harvest news use case instance."""
    return HarvestNewsUseCase(
        scrapers=build_news_scrapers(),
        repository=get_repository(),
        keyword_extractor=get_keyword_extractor(),
        skip_store=SkippedUrlStore(),
    )


def get_harvest_market_prices_use_case() -> HarvestMarketPricesUseCase:
    """Get harvest market prices use case instance."""
    return HarvestMarketPricesUseCase(
        scraper=ESXScraper(),
        repository=get_market_price_repository()
    )


def get_get_market_prices_use_case() -> GetMarketPricesUseCase:
    """Get get market prices use case instance."""
    return GetMarketPricesUseCase(repository=get_market_price_repository())


def get_get_news_use_case() -> GetNewsUseCase:
    """Get get news use case instance."""
    return GetNewsUseCase(repository=get_repository())


def get_filter_news_use_case() -> FilterNewsUseCase:
    """Get filter news use case instance."""
    return FilterNewsUseCase(keyword_extractor=get_keyword_extractor())
