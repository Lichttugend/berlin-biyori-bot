"""Scraper Agent — RSS フィードからベルリンのニュースを収集する"""

import feedparser
from datetime import datetime, timezone
from typing import Optional

FEEDS = [
    {"source": "rbb24", "url": "https://www.rbb24.de/aktuell/index.xml"},
    {"source": "berlin.de", "url": "https://www.berlin.de/aktuelles/rss.xml"},
    {"source": "berliner-zeitung", "url": "https://www.berliner-zeitung.de/feed.xml"},
    {"source": "tagesspiegel", "url": "https://www.tagesspiegel.de/feed.rss"},
    {"source": "tagesschau", "url": "https://www.tagesschau.de/xml/rss2/"},
]

MAX_SUMMARY_LENGTH = 500
MAX_ARTICLES_PER_FEED = 3


def _parse_published(entry) -> str:
    """feedparser のエントリから ISO 8601 文字列を返す"""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        return dt.isoformat()
    return datetime.now(timezone.utc).isoformat()


def _extract_summary(entry) -> str:
    """要約または本文の先頭 MAX_SUMMARY_LENGTH 字を返す"""
    text = ""
    if hasattr(entry, "summary") and entry.summary:
        text = entry.summary
    elif hasattr(entry, "description") and entry.description:
        text = entry.description
    # HTML タグを除去（簡易）
    import re
    text = re.sub(r"<[^>]+>", "", text).strip()
    return text[:MAX_SUMMARY_LENGTH]


def fetch_articles(posted_urls: set[str]) -> list[dict]:
    """全フィードから未投稿の記事を収集して返す"""
    articles = []
    for feed_info in FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            count = 0
            for entry in feed.entries:
                if count >= MAX_ARTICLES_PER_FEED:
                    break
                url = getattr(entry, "link", "") or ""
                if not url or url in posted_urls:
                    continue
                title = (getattr(entry, "title", "") or "").strip()
                if not title:
                    continue
                articles.append(
                    {
                        "url": url,
                        "title": title,
                        "summary": _extract_summary(entry),
                        "published": _parse_published(entry),
                        "source": feed_info["source"],
                    }
                )
                count += 1
        except Exception as e:
            print(f"[scraper] {feed_info['source']} の取得に失敗: {e}")
    return articles
