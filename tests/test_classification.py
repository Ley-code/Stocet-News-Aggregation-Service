"""Classifier behaviour: whole-word matching, headline/body thresholds, relevance rules."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.infrastructure.nlp.keyword_extractor import KeywordExtractor  # noqa: E402


class ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.k = KeywordExtractor()

    def test_whole_words_only(self):
        # "NBE" must not match inside another word
        self.assertNotIn("Treasury Bills", self.k.classify("Nbears and bulls", ""))
        self.assertIn("Treasury Bills", self.k.classify("NBE holds T-Bill auction", ""))

    def test_single_body_mention_is_not_a_topic(self):
        self.assertEqual(self.k.classify("Weekend football roundup", "The club took out a loan."), set())

    def test_two_body_mentions_tag_category(self):
        cats = self.k.classify("Quarterly report", "Deposits grew while loans expanded at the bank.")
        self.assertIn("Banking", cats)

    def test_headline_hit_is_enough(self):
        self.assertIn("Insurance", self.k.classify("Insurance premiums climb", ""))

    def test_regional_feed_needs_ethiopia(self):
        cats = {"Banking"}
        self.assertFalse(self.k.is_relevant("Kenya bank profits rise", set()))
        self.assertTrue(self.k.is_relevant("Kenya bank profits rise", cats))  # core category passes
        self.assertFalse(self.k.is_relevant("New dam planned", {"Energy & Infrastructure"}))
        self.assertTrue(self.k.is_relevant("New dam planned in Ethiopia", {"Energy & Infrastructure"}))

    def test_domestic_source_accepts_any_category(self):
        self.assertTrue(self.k.is_relevant("New dam planned", {"Energy & Infrastructure"}, domestic=True))


if __name__ == "__main__":
    unittest.main()
