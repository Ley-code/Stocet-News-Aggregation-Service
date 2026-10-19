"""Utility to trigger alert matching on the Core Service after price updates."""
import httpx
from loguru import logger
from ..infrastructure.config import settings


def trigger_alerts() -> None:
    """Send a POST request to the Core Service to trigger alert matching.

    Called after market prices are persisted. Failures are logged but never
    crash the main scraper process.
    """
    # core_service_url already includes the /api/v1 prefix, so we only append
    # the endpoint path here (appending /api/v1 again would 404).
    url = f"{settings.core_service_url}/internal/trigger-alerts"
    # The Core Service guards this endpoint with InternalSecretMiddleware and
    # rejects unauthenticated calls with 401, so the shared secret is required.
    headers = {"X-Internal-Secret": settings.internal_secret}
    try:
        response = httpx.post(url, headers=headers, timeout=30.0)
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
