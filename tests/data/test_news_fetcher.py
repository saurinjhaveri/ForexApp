import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import patch
from data.news_fetcher import fetch_news, NewsItem, flag_keywords

MOCK_FEED = {
    "entries": [
        {
            "title": "RBI intervention in forex market caps rupee fall",
            "link": "https://reuters.com/article/1",
            "published": "Sat, 03 May 2026 08:00:00 +0000",
            "summary": "RBI sold dollars to cap rupee depreciation.",
        },
        {
            "title": "India Nifty hits record high",
            "link": "https://reuters.com/article/2",
            "published": "Sat, 03 May 2026 07:00:00 +0000",
            "summary": "Equity rally continues.",
        },
    ]
}

def test_fetch_news_returns_news_items():
    with patch("data.news_fetcher.feedparser.parse", return_value=MOCK_FEED):
        items = fetch_news()
    assert len(items) == 2
    assert all(isinstance(i, NewsItem) for i in items)

def test_flag_keywords_detects_rbi_intervention():
    with patch("data.news_fetcher.feedparser.parse", return_value=MOCK_FEED):
        items = fetch_news()
    flagged = [i for i in items if i.flagged]
    assert len(flagged) == 1
    assert "rbi intervention" in flagged[0].matched_keywords

def test_flag_keywords_standalone():
    assert "fed" in flag_keywords("Fed raises rates by 25 bps")
    assert "tariff" in flag_keywords("New tariff on Indian steel exports")
    assert flag_keywords("Nifty closes flat") == []
