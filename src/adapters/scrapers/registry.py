"""All configured news sources in one place. Add a feed here to add a source."""
from typing import List
from ...domain.interfaces import BaseScraper
from .capital_ethiopia import CapitalEthiopiaScraper
from .esx import ESXScraper
from .rss import RSSScraper

# Regional / global feeds only keep stories that mention Ethiopia.
_ETHIOPIA_TERMS = ["ethiopia", "ethiopian", "addis ababa", "birr"]

# (source name, feed url, site url, required terms)
RSS_SOURCES = [
    ("Addis Fortune", "https://addisfortune.news/feed/", "https://addisfortune.news", None),
    ("Ethiopian Business Review", "https://ethiopianbusinessreview.net/feed/", "https://ethiopianbusinessreview.net", None),
    ("Birr Metrics", "https://birrmetrics.com/feed/", "https://birrmetrics.com", None),
    ("Ethiopia Insight", "https://www.ethiopia-insight.com/feed/", "https://www.ethiopia-insight.com", None),
    ("Fana Broadcasting", "https://www.fanabc.com/feed/", "https://www.fanabc.com", None),
    ("Ethiopian Monitor", "https://www.ethiopianmonitor.com/feed/", "https://www.ethiopianmonitor.com", None),
    ("Shega", "https://shega.co/rss", "https://shega.co", None),
    ("BBC Africa", "https://feeds.bbci.co.uk/news/world/africa/rss.xml", "https://www.bbc.com", _ETHIOPIA_TERMS),
    ("The Africa Report", "https://www.theafricareport.com/feed/", "https://www.theafricareport.com", _ETHIOPIA_TERMS),
]


def build_news_scrapers() -> List[BaseScraper]:
    scrapers: List[BaseScraper] = [CapitalEthiopiaScraper(), ESXScraper()]
    scrapers += [RSSScraper(name, feed, site, terms) for name, feed, site, terms in RSS_SOURCES]
    return scrapers
