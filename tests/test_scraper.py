"""Scraper Agent のテスト"""

from unittest.mock import MagicMock, patch
from agents.scraper import fetch_articles, _extract_summary, _parse_published


def _make_entry(title="Test Title", link="https://example.com/1", summary="Some text"):
    entry = MagicMock()
    entry.title = title
    entry.link = link
    entry.summary = summary
    entry.published_parsed = (2026, 4, 7, 10, 0, 0, 0, 0, 0)
    return entry


def test_fetch_articles_skips_posted_urls():
    posted = {"https://example.com/1"}
    entry = _make_entry(link="https://example.com/1")
    feed = MagicMock()
    feed.entries = [entry]

    with patch("agents.scraper.feedparser.parse", return_value=feed):
        articles = fetch_articles(posted)

    assert all(a["url"] != "https://example.com/1" for a in articles)


def test_fetch_articles_returns_new_articles():
    posted: set[str] = set()
    entry = _make_entry()
    feed = MagicMock()
    feed.entries = [entry]

    with patch("agents.scraper.feedparser.parse", return_value=feed):
        articles = fetch_articles(posted)

    assert len(articles) > 0
    assert articles[0]["title"] == "Test Title"
    assert articles[0]["url"] == "https://example.com/1"
    assert "source" in articles[0]
    assert "published" in articles[0]


def test_extract_summary_strips_html():
    entry = MagicMock()
    entry.summary = "<p>Hello <b>World</b></p>"
    result = _extract_summary(entry)
    assert "<" not in result
    assert "Hello World" in result


def test_extract_summary_truncates():
    entry = MagicMock()
    entry.summary = "x" * 600
    result = _extract_summary(entry)
    assert len(result) == 500
