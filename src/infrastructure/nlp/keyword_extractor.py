"""Keyword-based classifier for financial news."""
import re
from typing import Dict, List, Set
from loguru import logger
from .taxonomy import CORE_CATEGORIES, FINANCIAL_TAXONOMY, get_all_keywords


def _compile(keywords: List[str]) -> re.Pattern:
    # Longest first so "Treasury Bills" wins over "Treasury"; word boundaries stop "NBE" matching inside other words.
    ordered = sorted(keywords, key=len, reverse=True)
    return re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(k) for k in ordered) + r")(?![A-Za-z0-9])", re.IGNORECASE)


_ETHIOPIA = re.compile(r"\b(ethiopia|ethiopian|addis ababa|addis|birr|oromia|amhara|tigray)\b", re.IGNORECASE)


class KeywordExtractor:
    """Extract financial keywords and categories from text using whole-word matching."""

    def __init__(self):
        self._patterns: Dict[str, re.Pattern] = {c: _compile(kw) for c, kw in FINANCIAL_TAXONOMY.items()}
        self._all = _compile(get_all_keywords())
        logger.info(f"Initialized keyword extractor with {len(get_all_keywords())} keywords")

    def extract_keywords(self, text: str) -> Set[str]:
        """Return the distinct taxonomy keywords found in the text."""
        if not text:
            return set()
        return {m.group(0).lower() for m in self._all.finditer(text)}

    def extract_categories(self, text: str) -> Set[str]:
        """Return the category tags whose keywords appear in the text."""
        if not text:
            return set()
        return {c for c, p in self._patterns.items() if p.search(text)}

    def classify(self, title: str, body: str) -> Set[str]:
        """Categories with a headline hit, or at least two distinct body hits (one stray word isn't a topic)."""
        found: Set[str] = set()
        for category, pattern in self._patterns.items():
            if pattern.search(title or ""):
                found.add(category)
                continue
            hits = {m.group(0).lower() for m in pattern.finditer(body or "")}
            if len(hits) >= 2:
                found.add(category)
        return found

    def mentions_ethiopia(self, text: str) -> bool:
        return bool(text and _ETHIOPIA.search(text))

    def is_relevant(self, text: str, categories: Set[str], domestic: bool = False) -> bool:
        """Relevant if it hits a core market category, or any category while being about Ethiopia."""
        if domestic and categories:
            return True
        if categories & CORE_CATEGORIES:
            return True
        return bool(categories) and self.mentions_ethiopia(text)

    def has_financial_relevance(self, text: str) -> bool:
        return len(self.extract_keywords(text)) > 0
