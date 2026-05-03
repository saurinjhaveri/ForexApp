from dataclasses import dataclass, field
from typing import List
import feedparser
from config import REUTERS_INDIA_RSS, FLAG_KEYWORDS


@dataclass
class NewsItem:
    title: str
    url: str
    published: str
    summary: str
    flagged: bool = False
    matched_keywords: List[str] = field(default_factory=list)


def flag_keywords(text: str) -> List[str]:
    text_lower = text.lower()
    return [kw for kw in FLAG_KEYWORDS if kw in text_lower]


def fetch_news(max_items: int = 20) -> List[NewsItem]:
    feed = feedparser.parse(REUTERS_INDIA_RSS)
    items = []
    for entry in feed.get("entries", [])[:max_items]:
        title   = entry.get("title", "")
        summary = entry.get("summary", "")
        combined = f"{title} {summary}"
        matched = flag_keywords(combined)
        items.append(NewsItem(
            title=title,
            url=entry.get("link", ""),
            published=entry.get("published", ""),
            summary=summary,
            flagged=len(matched) > 0,
            matched_keywords=matched,
        ))
    return items
