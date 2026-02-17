"""FastAPI application main file."""
import json
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from ..infrastructure.config import settings
from ..infrastructure.logging_config import configure_logging
from ..infrastructure.database.connection import init_database, close_database
from .routes import news
from .dependencies import get_harvest_news_use_case

# Configure logging
configure_logging()


def _debug_log(session_id, run_id, hypothesis_id, location, message, data=None):
    """Helper function for debug logging."""
    try:
        with open('/home/leykun/Desktop/NewsAggregationSystem/.cursor/debug.log', 'a') as f:
            import time
            f.write(json.dumps({
                "sessionId": session_id,
                "runId": run_id,
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data or {},
                "timestamp": time.time() * 1000
            }) + '\n')
    except Exception:
        pass


# Global scheduler instance
try:
    scheduler = AsyncIOScheduler()
    # #region agent log
    _debug_log("debug-session", "run1", "C", "main.py:scheduler_created", "Scheduler created", {})
    # #endregion
except Exception as e:
    # #region agent log
    _debug_log("debug-session", "run1", "C", "main.py:scheduler_creation_error", "Scheduler creation failed", {"error":str(e),"traceback":traceback.format_exc()})
    # #endregion
    raise


async def quick_harvest_job():
    """Quick harvest job - runs every 30 minutes."""
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Ethiopian Financial News Aggregation System...")
    await init_database()
    
    # Start scheduler
    scheduler.add_job(
        quick_harvest_job,
        trigger=IntervalTrigger(minutes=1),
        id="quick_harvest",
        name="Quick Harvest (every 30 minutes)",
        replace_existing=True
    )
    
    scheduler.add_job(
        deep_archive_job,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="deep_archive",
        name="Deep Archive (weekly on Sunday at 2 AM)",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started")
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    scheduler.shutdown()
    await close_database()
    logger.info("Application shut down")


# Create FastAPI app
app = FastAPI(
    title="Ethiopian Financial News Aggregation API",
    description="API for aggregating and querying financial news from Ethiopian sources",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(news.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Ethiopian Financial News Aggregation API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/v1/harvest")
async def harvest_news():
    """Manually trigger news harvesting."""
    try:
        use_case = get_harvest_news_use_case()
        count = await use_case.execute(limit_per_source=10)
        return {
            "message": "Harvest completed",
            "articles_saved": count
        }
    except Exception as e:
        logger.error(f"Harvest failed: {e}")
        return {
            "message": "Harvest failed",
            "error": str(e)
        }

