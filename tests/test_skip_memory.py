"""A harvest remembers articles it judged irrelevant, so the next run doesn't download them again."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.domain.entities import NewsArticle  # noqa: E402
from src.domain.interfaces import NewsRepository  # noqa: E402
from src.infrastructure.nlp.keyword_extractor import KeywordExtractor  # noqa: E402
from src.use_cases import harvest_news as hn  # noqa: E402


class MemRepo(NewsRepository):
    def __init__(self):
        self.d = {}

    async def save(self, a):
        if a.url in self.d:
            return False
        self.d[a.url] = a
        return True

    async def find_by_url(self, u):
        return self.d.get(u)

    async def find_all(self, *a, **k):
        return []


class MemSkip:
    def __init__(self):
        self.urls = set()

    async def load(self):
        return len(self.urls)

    def is_skipped(self, u):
        return u in self.urls

    async def mark(self, u, source=None):
        self.urls.add(u)


class FakeScraper:
    """Counts how many pages it 'downloads'; skips URLs the use case says are already known."""
    source_name = "Fake"
    domestic = True
    is_known = None

    def __init__(self):
        self.downloads = 0

    async def connect(self): ...
    async def disconnect(self): ...

    async def fetch_latest_articles(self, limit=10):
        out = []
        for url, title, body in [
            ("https://x/relevant", "Awash Bank profit rises", "Deposits grew and loans expanded at the bank."),
            ("https://x/noise", "Weekend football roundup", "The match ended in a draw."),
        ]:
            if await self.is_known(url):
                continue
            self.downloads += 1
            out.append(NewsArticle(title=title, url=url, source="Fake", published_date=datetime.now(timezone.utc), content=body))
        return out


class SkipMemoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_irrelevant_article_is_not_downloaded_twice(self):
        hn.trigger_sentiment = lambda *a, **k: None  # no network in tests
        repo, skip, scraper = MemRepo(), MemSkip(), FakeScraper()
        uc = hn.HarvestNewsUseCase([scraper], repo, KeywordExtractor(), skip_store=skip)

        await uc.execute()
        self.assertEqual(scraper.downloads, 2)          # first run looks at both
        self.assertIn("https://x/relevant", repo.d)     # relevant one stored
        self.assertIn("https://x/noise", skip.urls)     # irrelevant one remembered

        await uc.execute()
        self.assertEqual(scraper.downloads, 2)          # second run downloads nothing new


if __name__ == "__main__":
    unittest.main()
