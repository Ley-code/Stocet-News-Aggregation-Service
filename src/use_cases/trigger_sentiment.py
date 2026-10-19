"""Ask the Core Service to classify the sentiment of newly stored articles."""
import httpx
from loguru import logger
from ..infrastructure.config import settings


def trigger_sentiment(batch: int = 30) -> None:
    """POST to Core's internal sentiment endpoint. Best effort: failures are logged, never raised."""
    url = f"{settings.core_service_url}/internal/sentiment/backfill"
    try:
        response = httpx.post(
            url,
            params={"batch": batch},
            headers={"X-Internal-Secret": settings.internal_secret},
            timeout=120.0,
        )
        if response.is_success:
            processed = response.json().get("data", {}).get("processed", 0)
            logger.info(f"Sentiment backfill triggered: {processed} articles analysed")
        else:
            logger.warning(f"Sentiment trigger returned {response.status_code}: {response.text[:200]}")
    except Exception as e:
        logger.warning(f"Could not trigger sentiment backfill: {e}")
