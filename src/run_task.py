"""Run one harvest task and exit. This is what the scheduled GitHub Actions workflow calls.

    python -m src.run_task news
    python -m src.run_task market_prices

Exits non-zero when the task fails, so a broken run shows up red in the Actions tab.
"""
import asyncio
import json
import sys

from loguru import logger

from .api.dependencies import get_harvest_market_prices_use_case, get_harvest_news_use_case
from .api.main import close_databases, connect_databases


async def news() -> dict:
    use_case = get_harvest_news_use_case()
    saved = await use_case.execute(limit_per_source=15)
    sources = use_case.summary()
    if sources and all(r["error"] for r in sources.values()):
        raise RuntimeError(f"every source failed: {json.dumps(sources)[:500]}")
    return {"articles_saved": saved, "sources": sources}


async def market_prices() -> dict:
    saved = await get_harvest_market_prices_use_case().execute()
    return {"prices_saved": saved}


TASKS = {"news": news, "market_prices": market_prices}


async def run(task: str) -> dict:
    await connect_databases()
    try:
        return await TASKS[task]()
    finally:
        await close_databases()


def main(argv: list) -> int:
    if len(argv) != 2 or argv[1] not in TASKS:
        print(f"usage: python -m src.run_task [{'|'.join(TASKS)}]", file=sys.stderr)
        return 2
    try:
        result = asyncio.run(run(argv[1]))
    except Exception as e:
        logger.error(f"Task {argv[1]} failed: {e}")
        return 1
    print(json.dumps(result, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
