import asyncio
import logging
from mangum import Mangum
from src.api.main import app, harvest_news, market_price_job, lifespan

# Ensure logger config
logger = logging.getLogger()
logger.setLevel(logging.INFO)

asgi_handler = Mangum(app)

async def run_with_lifespan(func):
    """Reusable helper to run tasks with proper DB initializations."""
    async with lifespan(app):
        return await func()

def lambda_handler(event, context):
    logger.info("Lambda invocation started.")
    
    # Check if triggered by EventBridge cron or explicit task payload
    if event.get("source") == "aws.events" or "task" in event:
        logger.info("EventBridge / Task trigger detected. Bypassing HTTP and running internal logic.")
        try:
            task = event.get("task")
            if task == "news":
                logger.info("Running task: news")
                result = asyncio.run(run_with_lifespan(harvest_news))
                logger.info(f"News harvesting completed: {result}")
                return {"status": "success", "task": "news", "result": result}
                
            elif task == "market_prices":
                logger.info("Running task: market_prices")
                result = asyncio.run(run_with_lifespan(market_price_job))
                logger.info("Market price scraping completed.")
                return {"status": "success", "task": "market_prices", "result": result}
                
            else:
                logger.warning(f"Unknown or missing task provided: {task}. Gracefully exiting.")
                return {"status": "warning", "message": f"Unknown or missing task: {task}"}
                
        except Exception as e:
            logger.error(f"Error during scheduled task execution: {e}")
            raise

    # Otherwise treat as normal HTTP request via API Gateway or Function URL
    logger.info("Treating event as normal HTTP request.")
    return asgi_handler(event, context)
