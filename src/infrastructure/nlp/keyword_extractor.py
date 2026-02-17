"""FlashText-based keyword extractor for financial news."""
from flashtext import KeywordProcessor
from typing import List, Set
from loguru import logger
from .taxonomy import FINANCIAL_TAXONOMY, get_all_keywords


class KeywordExtractor:
    """Extract financial keywords from text using FlashText algorithm."""
    
    def __init__(self):
        """Initialize the keyword processor with financial taxonomy."""
        self.processor = KeywordProcessor()
        self._build_keyword_processor()
    
    def _build_keyword_processor(self) -> None:
        """Build the FlashText keyword processor with all taxonomy keywords."""
        for category, keywords in FINANCIAL_TAXONOMY.items():
            for keyword in keywords:
                # Use case-insensitive matching
                self.processor.add_keyword(keyword.lower(), keyword)
        
        logger.info(f"Initialized keyword extractor with {len(get_all_keywords())} keywords")
    
    def extract_keywords(self, text: str) -> Set[str]:
        """Extract financial keywords from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Set of matched keywords
        """
        if not text:
            return set()
        
        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()
        found_keywords = self.processor.extract_keywords(text_lower)
        
        return set(found_keywords)
    
    def extract_categories(self, text: str) -> Set[str]:
        """Extract category tags based on found keywords.
        
        Args:
            text: Text to analyze
            
        Returns:
            Set of category names that matched
        """
        if not text:
            return set()
        
        categories = set()
        text_lower = text.lower()
        
        for category, keywords in FINANCIAL_TAXONOMY.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    categories.add(category)
                    break  # Found at least one keyword in this category
        
        return categories
    
    def has_financial_relevance(self, text: str) -> bool:
        """Check if text has financial relevance.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if text contains at least one financial keyword
        """
        keywords = self.extract_keywords(text)
        return len(keywords) > 0

