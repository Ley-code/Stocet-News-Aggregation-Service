"""Financial keyword taxonomy for Ethiopian markets."""
from typing import Dict, List


FINANCIAL_TAXONOMY: Dict[str, List[str]] = {
    "Treasury Bills": [
        "T-Bill",
        "Treasury Bill",
        "Treasury Bills",
        "28-day bill",
        "91-day bill",
        "182-day bill",
        "364-day bill",
        "Yield",
        "Auction",
        "National Bank of Ethiopia",
        "NBE",
        "Government Securities",
        "Treasury Bond",
        "Treasury Bonds"
    ],
    "Capital Markets": [
        "ESX",
        "Ethiopian Securities Exchange",
        "Stock Exchange",
        "IPO",
        "Initial Public Offering",
        "Shareholder",
        "Shareholders",
        "Dividend",
        "Dividends",
        "Equity",
        "Brook Taye",
        "Securities",
        "Trading",
        "Market Capitalization",
        "Listing"
    ],
    "Macroeconomics": [
        "Inflation",
        "CPI",
        "Consumer Price Index",
        "GDP",
        "Gross Domestic Product",
        "Forex",
        "Foreign Exchange",
        "Exchange Rate",
        "Exchange Rates",
        "Birr",
        "ETB",
        "IMF",
        "International Monetary Fund",
        "World Bank",
        "Liberalization",
        "Economic Growth",
        "Monetary Policy",
        "Fiscal Policy",
        "Central Bank"
    ],
    "Politics": [
        "Proclamation",
        "Parliament",
        "Abiy Ahmed",
        "Ministry of Finance",
        "Ministry of Finance and Economic Cooperation",
        "Regulation",
        "Regulations",
        "Policy",
        "Government",
        "Cabinet",
        "Prime Minister"
    ]
}


def get_all_keywords() -> List[str]:
    """Get all keywords from all categories."""
    keywords = []
    for category_keywords in FINANCIAL_TAXONOMY.values():
        keywords.extend(category_keywords)
    return keywords


def get_keywords_by_category(category: str) -> List[str]:
    """Get keywords for a specific category."""
    return FINANCIAL_TAXONOMY.get(category, [])

