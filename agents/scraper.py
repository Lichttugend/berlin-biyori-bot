"""Scraper Agent — RSS フィードからベルリンのニュースを収集する"""

import feedparser
import httpx
from datetime import datetime, timezone
from typing import Optional

FEED_TIMEOUT_SECONDS = 15

FEEDS = [
    # ベルリン・ブランデンブルク専門（フィルタ不要）
    {"source": "rbb24", "url": "https://www.rbb24.de/berlin/index.xml/feed=rss.xml", "berlin_only": False},
    # ベルリン地元紙だが国際記事も混在するためフィルタあり
    {"source": "berliner-zeitung", "url": "https://www.berliner-zeitung.de/feed.xml", "berlin_only": True},
    {"source": "morgenpost", "url": "https://www.morgenpost.de/rss", "berlin_only": True},
    {"source": "tagesspiegel", "url": "https://www.tagesspiegel.de/news.xml", "berlin_only": True},
]

# ベルリン固有のキーワード（単独でベルリン関連と判定できる）
BERLIN_SPECIFIC_KEYWORDS = [
    "berlin", "berliner", "berlins",
    "bvg", "s-bahn", "u-bahn", "s bahn", "u bahn",
    "senat", "abgeordnetenhaus",
    "mitte", "prenzlauer", "kreuzberg", "neukölln", "neukoelln",
    "charlottenburg", "friedrichshain", "spandau", "steglitz",
    "tempelhof", "treptow", "lichtenberg", "marzahn", "pankow",
    "reinickendorf", "köpenick", "koepenick",
    "brandenburg",
]

# 国レベルのキーワード（単独では不十分。ベルリン固有キーワードとの共出現が必要）
# 例: 「bundesregierung beschließt...」だけではベルリン関連とは言えない
GERMANY_GENERAL_KEYWORDS = [
    "deutschland", "deutsch", "german",
    "bundesregierung", "bundestag", "bundesrat",
]

MAX_SUMMARY_LENGTH = 500
MAX_ARTICLES_PER_FEED = 3


def _is_berlin_related(title: str, summary: str) -> bool:
    """タイトルまたはサマリーにベルリン関連キーワードが含まれるか判定。

    ベルリン固有キーワードが1つでもあれば対象。
    国レベルキーワード（bundesregierung 等）は単独では不十分で、
    ベルリン固有キーワードとの共出現が必要。
    """
    text = (title + " " + summary).lower()
    if any(kw in text for kw in BERLIN_SPECIFIC_KEYWORDS):
        return True
    # 国レベルキーワード単独ではベルリン関連と判定しない
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
                    }
                )
                count += 1
        except Exception as e:
            print(f"[scraper] {feed_info['source']} の取得に失敗: {e}")
    return articles
