"""Utility to trigger alert matching on the Core Service after price updates."""
import httpx
from loguru import logger
from ..infrastructure.config import settings


def trigger_alerts() -> None:
    """Send a POST request to the Core Service to trigger alert matching.

    Called after market prices are persisted. Failures are logged but never
    crash the main scraper process.
    """
    url = f"{settings.core_service_url}/api/v1/internal/trigger-alerts"
    try:
        response = httpx.post(url, timeout=30.0)
        if response.is_success:
            data = response.json()
            logger.info(
                f"Alert trigger successful: {data.get('data', {}).get('triggered', 0)} alerts matched"
            )
        else:
            logger.warning(
                f"Alert trigger returned {response.status_code}: {response.text}"
            )
    except httpx.ConnectError:
        logger.warning(f"Could not connect to Core Service at {url} – skipping alert trigger")
    except Exception as e:
        logger.error(f"Failed to trigger alerts: {e}")
