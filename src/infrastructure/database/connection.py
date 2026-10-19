"""MongoDB connection setup using Motor and Beanie."""
import json
import traceback
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from loguru import logger
from ..config import settings
from .models import NewsArticleDocument, MarketPriceDocument

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


async def init_database() -> None:
    """Initialize MongoDB connection and Beanie ODM."""
    # #region agent log
    _debug_log("debug-session", "run1", "B", "connection.py:init_db_start", "init_database started", {"mongodb_url":settings.mongodb_url[:30]+"..."})
    # #endregion
    try:
        # #region agent log
        _debug_log("debug-session", "run1", "B", "connection.py:before_motor_client", "Before AsyncIOMotorClient", {})
        # #endregion
        # Fail fast when Mongo is down instead of hanging for the 30s default.
        client = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=5000)
        # #region agent log
        _debug_log("debug-session", "run1", "B", "connection.py:after_motor_client", "After AsyncIOMotorClient", {})
        # #endregion
        database = client[settings.mongodb_db_name]
        # #region agent log
        _debug_log("debug-session", "run1", "B", "connection.py:before_init_beanie", "Before init_beanie", {"db_name":settings.mongodb_db_name})
        # #endregion
        await init_beanie(
            database=database,
            document_models=[NewsArticleDocument, MarketPriceDocument]
        )
        # #region agent log
        _debug_log("debug-session", "run1", "B", "connection.py:after_init_beanie", "After init_beanie", {})
        # #endregion
        logger.info(f"Connected to MongoDB: {settings.mongodb_db_name}")
    except Exception as e:
        # #region agent log
        _debug_log("debug-session", "run1", "B", "connection.py:init_db_error", "init_database failed", {"error":str(e),"traceback":traceback.format_exc()})
        # #endregion
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_database() -> None:
    """Close MongoDB connection."""
    logger.info("Closing MongoDB connection")

