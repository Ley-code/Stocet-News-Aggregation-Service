"""Configuration management using pydantic-settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # MongoDB Configuration
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "ethiopian_financial_news"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # Scraping Configuration
    rate_limit_delay: int = 5  # seconds between requests
    circuit_breaker_threshold: int = 5  # consecutive errors before disabling
    circuit_breaker_timeout: int = 3600  # seconds before retry
    
    # User Agent
    user_agent: str = "EthiopianFinancialIntelBot/1.0 (+https://github.com/your-repo/bot-policy)"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

