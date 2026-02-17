"""FastAPI dependency injection."""
from functools import lru_cache
from ..adapters.scrapers.addis_fortune import AddisFortuneScraper
from ..adapters.scrapers.capital_ethiopia import CapitalEthiopiaScraper
# from ..adapters.scrapers.reuters import ReutersScraper
from ..adapters.repositories.mongo_repository import MongoNewsRepository
from ..infrastructure.nlp.keyword_extractor import KeywordExtractor
from ..use_cases.harvest_news import HarvestNewsUseCase
from ..use_cases.get_news import GetNewsUseCase
from ..use_cases.filter_news import FilterNewsUseCase


@lru_cache()
def get_keyword_extractor() -> KeywordExtractor:
    """Get keyword extractor instance."""
    return KeywordExtractor()


@lru_cache()
def get_repository() -> MongoNewsRepository:
    """Get MongoDB repository instance."""
    return MongoNewsRepository()


def get_harvest_news_use_case() -> HarvestNewsUseCase:
    """Get harvest news use case instance."""
    scrapers = [
        AddisFortuneScraper(),
        CapitalEthiopiaScraper(),
        # ReutersScraper()
    ]
    return HarvestNewsUseCase(
        scrapers=scrapers,
        repository=get_repository(),
        keyword_extractor=get_keyword_extractor()
    )


def get_get_news_use_case() -> GetNewsUseCase:
    """Get get news use case instance."""
    return GetNewsUseCase(repository=get_repository())


def get_filter_news_use_case() -> FilterNewsUseCase:
    """Get filter news use case instance."""
    return FilterNewsUseCase(keyword_extractor=get_keyword_extractor())

