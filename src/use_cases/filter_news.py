"""Use case for filtering news articles by keywords."""
from typing import List
from ..domain.entities import NewsArticle
from ..infrastructure.nlp.keyword_extractor import KeywordExtractor


class FilterNewsUseCase:
    """Applies keyword taxonomy to filter news articles."""
    
    def __init__(self, keyword_extractor: KeywordExtractor):
        """Initialize filter use case.
        
        Args:
            keyword_extractor: Keyword extractor instance
        """
        self.keyword_extractor = keyword_extractor
    
    def execute(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Filter articles by financial relevance.
        
        Args:
            articles: List of articles to filter
            
        Returns:
            Filtered list of articles with financial relevance
        """
        filtered = []
        
        for article in articles:
            # Check if article has financial keywords
            text = f"{article.title} {article.content}"
            if self.keyword_extractor.has_financial_relevance(text):
                # Extract and add tags
                categories = self.keyword_extractor.extract_categories(text)
                article.tags = list(categories)
                filtered.append(article)
        
        return filtered

