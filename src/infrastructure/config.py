"""Configuration management using pydantic-settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "ethiopian_financial_news"
    
    # Every harvest is written to PostgreSQL (source of truth, read by the Core service) and mirrored to MongoDB.
    # If Mongo is unreachable the run continues with PostgreSQL only. Set MONGO_ENABLED=false to skip Mongo.
    mongo_enabled: bool = True

    # PostgreSQL Configuration (dual-write target)
    postgres_dsn: str = "postgresql://postgres:postgres@localhost:5432/stocet_core?sslmode=disable"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # Scraping Configuration
    rate_limit_delay: int = 5  # seconds between requests
    circuit_breaker_threshold: int = 5  # consecutive errors before disabling
    circuit_breaker_timeout: int = 3600  # seconds before retry
    
    # Scheduler Configuration
    harvest_interval_hours: int = 2  # hours between harvest jobs (default: every 2 hours)
    market_price_scrape_interval_minutes: int = 1440  # minutes between market price scrapes (default: every day)
    
    # User Agent
    user_agent: str = "EthiopianFinancialIntelBot/1.0 (+https://github.com/your-repo/bot-policy)"
    
    # Core Service URL (for triggering alerts after price updates).
    # Includes the /api/v1 version prefix.
    core_service_url: str = "http://localhost:8080/api/v1"

    # Shared secret for service-to-service calls to the Core Service.
    # Must match the Core Service's INTERNAL_SECRET env var, otherwise
    # alert triggering is rejected with 401.
    internal_secret: str = ""

    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

