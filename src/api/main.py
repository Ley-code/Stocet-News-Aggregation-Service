"""FastAPI application main file.

This service acts as a background worker only.
It scrapes news and market data on a schedule and writes to the database.
All public API endpoints are served by Stocet-Core-Service.
"""
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from ..infrastructure.config import settings
from ..infrastructure.logging_config import configure_logging
from ..infrastructure.database.postgres_connection import init_postgres, close_postgres, get_pool
from .dependencies import get_harvest_news_use_case, get_harvest_market_prices_use_case, set_mongo_ready

# Configure logging
configure_logging()

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def quick_harvest_job():
    """Quick harvest job - runs at configured interval."""
    logger.info("Starting quick harvest job...")
    try:
        use_case = get_harvest_news_use_case()
        count = await use_case.execute(limit_per_source=10)
        logger.info(f"Quick harvest completed: {count} new articles saved")
    except Exception as e:
        logger.error(f"Quick harvest job failed: {e}")


async def deep_archive_job():
    """Deep archive job - runs once a week."""
    logger.info("Starting deep archive job...")
    try:
        use_case = get_harvest_news_use_case()
        count = await use_case.execute(limit_per_source=50)
        logger.info(f"Deep archive completed: {count} new articles saved")
    except Exception as e:
        logger.error(f"Deep archive job failed: {e}")


async def market_price_job():
    """Market price scraping job - runs at configured interval."""
    logger.info("Starting market price scraping job...")
    try:
        use_case = get_harvest_market_prices_use_case()
        count = await use_case.execute()
        logger.info(f"Market price scraping completed: {count} prices saved")
    except Exception as e:
        logger.error(f"Market price scraping job failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Ethiopian Financial News Aggregation Worker...")
    if settings.mongo_enabled:
        from ..infrastructure.database.connection import init_database
        try:
            await init_database()
            set_mongo_ready(True)
        except Exception as e:
            set_mongo_ready(False)
            logger.error(f"MongoDB unavailable, continuing with PostgreSQL only: {e}")
    await init_postgres()
    if get_pool() is None:
        # Fail loudly: silently "succeeding" without a database is how harvesting stopped unnoticed.
        raise RuntimeError("PostgreSQL is not reachable (check POSTGRES_DSN / network / security group)")

    is_lambda = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    if not is_lambda:
        # Start scheduler
        harvest_interval_hours = settings.harvest_interval_hours
        scheduler.add_job(
            quick_harvest_job,
            trigger=IntervalTrigger(hours=harvest_interval_hours),
            id="quick_harvest",
            name=f"Quick Harvest (every {harvest_interval_hours} hour{'s' if harvest_interval_hours != 1 else ''})",
            replace_existing=True,
        )
        logger.info(f"Harvest job scheduled to run every {harvest_interval_hours} hour{'s' if harvest_interval_hours != 1 else ''}")

        # Market price scraping job
        market_price_interval_minutes = settings.market_price_scrape_interval_minutes
        scheduler.add_job(
            market_price_job,
            trigger=IntervalTrigger(minutes=market_price_interval_minutes),
            id="market_price_scrape",
            name=f"Market Price Scrape (every {market_price_interval_minutes} minute{'s' if market_price_interval_minutes != 1 else ''})",
            replace_existing=True,
        )
        logger.info(f"Market price scraping job scheduled to run every {market_price_interval_minutes} minute{'s' if market_price_interval_minutes != 1 else ''}")

        scheduler.add_job(
            deep_archive_job,
            trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
            id="deep_archive",
            name="Deep Archive (weekly on Sunday at 2 AM)",
            replace_existing=True,
        )

        scheduler.start()
        logger.info("Scheduler started")
    else:
        logger.info("Running in AWS Lambda - bypassing APScheduler initialization")

    logger.info("Worker started successfully")

    yield

    # Shutdown
    logger.info("Shutting down worker...")
    is_lambda = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    if not is_lambda:
        scheduler.shutdown()
    await close_postgres()
    if settings.mongo_enabled:
        from ..infrastructure.database.connection import close_database
        await close_database()
    logger.info("Worker shut down")


# Create FastAPI app (minimal - only health check, no public API routes)
app = FastAPI(
    title="Ethiopian Financial News Aggregation Worker",
    description="Background worker for scraping and storing financial news and market data. All public APIs are served by Stocet-Core-Service.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Ethiopian Financial News Aggregation Worker",
        "version": "1.0.0",
        "note": "This service is a background worker only. Use Stocet-Core-Service for API access.",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/internal/harvest")
async def harvest_news():
    """Manually trigger news harvesting (internal use only)."""
    try:
        use_case = get_harvest_news_use_case()
        count = await use_case.execute(limit_per_source=15)
        return {"message": "Harvest completed", "articles_saved": count, "sources": use_case.summary()}
    except Exception as e:
        logger.error(f"Harvest failed: {e}")
        return {"message": "Harvest failed", "error": str(e)}

