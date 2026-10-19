"""Backfill news for a date range from the sources' public WordPress REST APIs.

Why: when harvesting is down, RSS only exposes the latest ~10-20 items, so older stories are lost.
WordPress sites also serve every post by date through /wp-json/wp/v2/posts, which lets us recover them.

Same pipeline as the live harvest: classify, drop irrelevant, save to PostgreSQL (+ Mongo mirror),
skip URLs already stored. Dry run by default.

    python -m scripts.backfill_news --since 2026-07-22 --until 2026-10-20            # dry run
    python -m scripts.backfill_news --since 2026-07-22 --until 2026-10-20 --apply    # write
"""
import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402
from loguru import logger  # noqa: E402

from src.adapters.scrapers.rss import _html_to_text  # noqa: E402
from src.api import dependencies as deps  # noqa: E402
from src.domain.entities import NewsArticle  # noqa: E402
from src.infrastructure.config import settings  # noqa: E402
from src.infrastructure.database.postgres_connection import close_postgres, init_postgres, get_pool  # noqa: E402
from src.infrastructure.nlp.keyword_extractor import KeywordExtractor  # noqa: E402

# source name -> site root (only sources whose posts API answered 200 and that are allowed by robots.txt)
SOURCES = {
    "Capital Ethiopia": "https://capitalethiopia.com",
    "Birr Metrics": "https://birrmetrics.com",
    "Ethiopian Business Review": "https://ethiopianbusinessreview.net",
    "Ethiopia Insight": "https://www.ethiopia-insight.com",
    "ESX": "https://esx.et",
}
FIELDS = "date_gmt,link,title,content,excerpt,jetpack_featured_media_url,yoast_head_json"
PER_PAGE = 50
DELAY = 1.0  # seconds between requests: be polite


def image_of(post: dict):
    if post.get("jetpack_featured_media_url"):
        return post["jetpack_featured_media_url"]
    og = (post.get("yoast_head_json") or {}).get("og_image") or []
    return og[0].get("url") if og else None


async def fetch_posts(client: httpx.AsyncClient, root: str, since: str, until: str):
    page = 1
    while True:
        r = await client.get(
            f"{root}/wp-json/wp/v2/posts",
            params={"after": f"{since}T00:00:00", "before": f"{until}T00:00:00", "per_page": PER_PAGE,
                    "page": page, "orderby": "date", "order": "desc", "_fields": FIELDS},
            timeout=60,
        )
        if r.status_code == 400:  # past the last page
            return
        r.raise_for_status()
        posts = r.json()
        if not posts:
            return
        for p in posts:
            yield p
        if len(posts) < PER_PAGE:
            return
        page += 1
        await asyncio.sleep(DELAY)


async def main(since: str, until: str, apply: bool):
    await init_postgres()
    if get_pool() is None:
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
    repo = deps.get_repository()
    kx = KeywordExtractor()

    headers = {"User-Agent": settings.user_agent, "Accept": "application/json"}
    grand = {"fetched": 0, "relevant": 0, "new": 0, "saved": 0}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        for source, root in SOURCES.items():
            c = {"fetched": 0, "relevant": 0, "new": 0, "saved": 0}
            try:
                async for p in fetch_posts(client, root, since, until):
                    c["fetched"] += 1
                    title = _html_to_text((p.get("title") or {}).get("rendered", ""))
                    content = _html_to_text((p.get("content") or {}).get("rendered", ""))
                    if not title or not p.get("link"):
                        continue
                    tags = sorted(kx.classify(title, content))
                    if not (source == "ESX" or kx.is_relevant(f"{title} {content}", set(tags), domestic=True)):
                        continue
                    c["relevant"] += 1
                    if await repo.find_by_url(p["link"]) is not None:
                        continue
                    c["new"] += 1
                    if not apply:
                        continue
                    summary = _html_to_text((p.get("excerpt") or {}).get("rendered", "")) or (
                        content[:300].rsplit(" ", 1)[0] + "…" if len(content) > 300 else content)
                    published = datetime.fromisoformat(p["date_gmt"]).replace(tzinfo=timezone.utc)
                    if await repo.save(NewsArticle(title=title, url=p["link"], source=source, published_date=published,
                                                   content=content or summary or title, summary=summary or None,
                                                   tags=tags, image_url=image_of(p))):
                        c["saved"] += 1
            except Exception as e:
                logger.error(f"{source}: backfill failed part-way: {e!r}")
            print(f"{source:28} fetched={c['fetched']:<4} relevant={c['relevant']:<4} new={c['new']:<4} saved={c['saved']}")
            for k in grand:
                grand[k] += c[k]
    print(f"{'TOTAL':28} fetched={grand['fetched']:<4} relevant={grand['relevant']:<4} new={grand['new']:<4} saved={grand['saved']}")
    print("(mirrored to MongoDB)" if mongo_ok else "(PostgreSQL only)", "| APPLIED" if apply else "| DRY RUN - nothing written")
    await close_postgres()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True)
    ap.add_argument("--until", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    asyncio.run(main(a.since, a.until, a.apply))
