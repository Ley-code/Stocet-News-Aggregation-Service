"""Bulk-copy rows that exist in PostgreSQL but not in MongoDB (articles by URL, prices by ticker+timestamp).

PostgreSQL is the source of truth; Mongo is a mirror. Use after a backfill or a Mongo outage. Dry run by default.

    python -m scripts.mirror_to_mongo            # dry run
    python -m scripts.mirror_to_mongo --apply
"""
import argparse
import asyncio
import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

from src.infrastructure.config import settings  # noqa: E402


def naive_utc(dt):
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt


async def main(apply: bool, price_since: str, price_source: str):
    pg = await asyncpg.connect(settings.postgres_dsn)
    mongo = AsyncIOMotorClient(settings.mongodb_url, serverSelectionTimeoutMS=15000)[settings.mongodb_db_name]

    have_urls = {d["url"] async for d in mongo.articles.find({}, {"url": 1})}
    arts = [r for r in await pg.fetch(
        "SELECT title,url,source,published_date,content,summary,tags,image_url FROM articles") if r["url"] not in have_urls]
    print(f"articles missing in Mongo: {len(arts)}")

    since = date.fromisoformat(price_since)
    rows = await pg.fetch(
        "SELECT ticker_symbol,price,percent_change,variation,timestamp,source FROM market_prices WHERE timestamp >= $1::date AND source = $2", since, price_source)
    have = {(d["ticker_symbol"], d["timestamp"].replace(microsecond=0))
            async for d in mongo.market_prices.find({"timestamp": {"$gte": datetime(since.year, since.month, since.day)}},
                                                    {"ticker_symbol": 1, "timestamp": 1})}
    prices = [r for r in rows if (r["ticker_symbol"], naive_utc(r["timestamp"]).replace(microsecond=0)) not in have]
    print(f"prices since {price_since} missing in Mongo: {len(prices)}")

    if not apply:
        print("DRY RUN - nothing written")
        return
    if arts:
        res = await mongo.articles.insert_many(
            [{"title": r["title"], "url": r["url"], "source": r["source"], "published_date": naive_utc(r["published_date"]),
              "content": r["content"], "summary": r["summary"], "tags": list(r["tags"] or []), "image_url": r["image_url"]}
             for r in arts], ordered=False)
        print("articles inserted:", len(res.inserted_ids))
    if prices:
        res = await mongo.market_prices.insert_many(
            [{"ticker_symbol": r["ticker_symbol"], "price": float(r["price"]), "percent_change": float(r["percent_change"]),
              "variation": float(r["variation"]), "timestamp": naive_utc(r["timestamp"]), "source": r["source"]} for r in prices],
            ordered=False)
        print("prices inserted:", len(res.inserted_ids))
    await pg.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--price-since", default="2026-07-23")
    ap.add_argument("--price-source", default="ESX (Aksion backfill)", help="only mirror prices with this source label")
    a = ap.parse_args()
    asyncio.run(main(a.apply, a.price_since, a.price_source))
