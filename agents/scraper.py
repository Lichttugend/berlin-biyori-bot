"""Scraper Agent — RSS フィードからベルリンのニュースを収集する"""

import feedparser
import httpx
from datetime import datetime, timezone
from typing import Optional

FEED_TIMEOUT_SECONDS = 15

FEEDS = [
    # ベルリン地元紙だが国際記事も混在するためフィルタあり
    {"source": "berliner-zeitung", "url": "https://www.berliner-zeitung.de/feed.xml", "berlin_only": True, "content_type": "news"},
    {"source": "morgenpost", "url": "https://www.morgenpost.de/rss", "berlin_only": True, "content_type": "news"},
    {"source": "tagesspiegel", "url": "https://www.tagesspiegel.de/news.xml", "berlin_only": True, "content_type": "news"},
    # ベルリンのイベント・カルチャー情報
    {"source": "tip-berlin", "url": "https://www.tip-berlin.de/feed/", "berlin_only": True, "content_type": "event"},
    # rbb24 文化・イベントニュース（ベルリン・ブランデンブルク）
    {"source": "rbb24-kultur", "url": "https://www.rbb24.de/kultur/index.xml/feed=rss.xml", "berlin_only": True, "content_type": "event"},
]

# 「berlin」系キーワード（これだけで確定）
BERLIN_KEYWORDS = [
    "berlin", "berliner", "berlins",
]

# 「berlin」なしでも確定できる固有名詞
BERLIN_UNAMBIGUOUS_KEYWORDS = [
    "bvg", "s-bahn", "u-bahn", "s bahn", "u bahn",
    "abgeordnetenhaus",
    "prenzlauer berg", "kreuzberg", "neukölln", "neukoelln",
    "charlottenburg", "friedrichshain", "tempelhof",
    "treptow", "lichtenberg", "marzahn", "reinickendorf",
    "köpenick", "koepenick",
]

MAX_SUMMARY_LENGTH = 500
MAX_ARTICLES_PER_FEED = 10


def _is_berlin_related(title: str, summary: str) -> bool:
    """タイトルまたはサマリーにベルリン関連キーワードが含まれるか判定。

    「berlin / berliner / berlins」が含まれるか、
    または曖昧性のないベルリン固有名詞が含まれる場合に True を返す。
    「mitte」「senat」「spandau」など一般語・他地域でも使われる語は除外。
    """
    text = (title + " " + summary).lower()
    if any(kw in text for kw in BERLIN_KEYWORDS):
        return True
    if any(kw in text for kw in BERLIN_UNAMBIGUOUS_KEYWORDS):
        return True
    return False


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
            response = httpx.get(feed_info["url"], timeout=FEED_TIMEOUT_SECONDS, follow_redirects=True)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
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
                summary = _extract_summary(entry)
                if feed_info["berlin_only"] and not _is_berlin_related(title, summary):
                    print(f"[scraper] スキップ（ベルリン無関係）: {title[:40]}")
                    continue
                articles.append(
                    {
                        "url": url,
                        "title": title,
                        "summary": summary,
                        "published": _parse_published(entry),
                        "source": feed_info["source"],
                        "content_type": feed_info.get("content_type", "news"),
                    }
                )
                count += 1
        except Exception as e:
            print(f"[scraper] {feed_info['source']} の取得に失敗: {e}")
    return articles
