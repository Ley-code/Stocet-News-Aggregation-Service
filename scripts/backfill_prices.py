"""Backfill market prices from daily OHLC candle files into PostgreSQL (+ Mongo mirror).

Input: JSON files shaped like {"ticker": "AWAB", "candles": [{"dateIso","open","high","low","close","variance"}, ...]}
(one file per ticker). The importer only fills (ticker, day) pairs that have NO rows yet, so prices we recorded
ourselves are never touched. Each imported row carries --source so it is identifiable and removable:

    DELETE FROM market_prices WHERE source = '<the label>';

A day becomes up to four rows (open, high, low, close at fixed times inside the ESX session) so the candle chart
keeps the true daily range. Dry run by default.

    python -m scripts.backfill_prices --files /tmp/aks_*.json --since 2026-07-23 --until 2026-10-19 \
        --source "ESX (Aksion backfill)"            # dry run; add --apply to write
"""
import argparse
import asyncio
import json
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loguru import logger  # noqa: E402

from src.api import dependencies as deps  # noqa: E402
from src.domain.entities import MarketPrice  # noqa: E402
from src.infrastructure.config import settings  # noqa: E402
from src.infrastructure.database.postgres_connection import close_postgres, get_pool, init_postgres  # noqa: E402

# Fixed UTC times inside the ESX session (order of high/low within a day is not known, so it is synthetic).
POINT_TIMES = {"open": time(6, 30), "high": time(8, 0), "low": time(9, 30), "close": time(11, 0)}


def day_points(c: dict, prev_close: float):
    """Distinct (label, price) points for one candle."""
    o, h, l, cl = c["open"], c["high"], c["low"], c["close"]
    if o == h == l == cl:
        return [("close", cl)]
    pts, seen = [], set()
    for label, p in (("open", o), ("high", h), ("low", l), ("close", cl)):
        # keep a repeated value only once, but always keep the close
        if p in seen and label != "close":
            continue
        seen.add(p)
        pts.append((label, p))
    return pts


async def main(files, since: date, until: date, source: str, apply: bool):
    await init_postgres()
    pool = get_pool()
    if pool is None:
        raise SystemExit("PostgreSQL not reachable")
    mongo_ok = False
    if settings.mongo_enabled:
        try:
            from src.infrastructure.database.connection import init_database
            await init_database()
            mongo_ok = True
        except Exception as e:
            logger.error(f"MongoDB unavailable, writing to PostgreSQL only: {e}")
    deps.set_mongo_ready(mongo_ok)
    repo = deps.get_market_price_repository()

    total_days = total_rows = 0
    for f in sorted(files):
        d = json.load(open(f))
        ticker = d["ticker"].upper()
        candles = sorted(d.get("candles") or [], key=lambda c: c["dateIso"])
        have = {r[0] for r in await pool.fetch(
            "SELECT DISTINCT timestamp::date FROM market_prices WHERE ticker_symbol=$1", ticker)}
        prev_close, days, rows = None, 0, 0
        for c in candles:
            day = date.fromisoformat(c["dateIso"])
            if prev_close is None:
                prev_close = c["open"]
            if since <= day <= until and day not in have:
                days += 1
                for label, price in day_points(c, prev_close):
                    base = prev_close or price
                    variation = round(price - base, 4)
                    pct = c["variance"] if label == "close" else (round(variation / base * 100, 2) if base else 0.0)
                    rows += 1
                    if apply:
                        ts = datetime.combine(day, POINT_TIMES[label], tzinfo=timezone.utc)
                        await repo.save(MarketPrice(ticker_symbol=ticker, price=float(price), percent_change=float(pct),
                                                    variation=float(variation), timestamp=ts, source=source))
            prev_close = c["close"]
        total_days += days
        total_rows += rows
        print(f"{ticker:6} candles in file={len(candles):<3} days filled={days:<3} rows={rows}")
    print(f"TOTAL days filled={total_days} rows={total_rows} | source label: {source!r}")
    print(("(mirrored to MongoDB) " if mongo_ok else "(PostgreSQL only) ") + ("| APPLIED" if apply else "| DRY RUN - nothing written"))
    await close_postgres()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="+", required=True)
    ap.add_argument("--since", required=True)
    ap.add_argument("--until", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    asyncio.run(main(a.files, date.fromisoformat(a.since), date.fromisoformat(a.until), a.source, a.apply))
