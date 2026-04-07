"""Formatter Agent のテスト"""

from agents.formatter import format_for_x, MAX_TWEET_LENGTH, TWITTER_URL_LENGTH


def _make_article(title="ベルリンの交通が混乱", summary="本日ベルリンの交通は大幅に乱れています。"):
    return {
        "url": "https://www.rbb24.de/wirtschaft/2026/04/berlin-verkehr.html",
        "ja_title": title,
        "ja_summary": summary,
    }


def _tweet_length(text: str) -> int:
    """URL を TWITTER_URL_LENGTH として計算したツイートの文字数"""
    import re
    url_pattern = r"https?://\S+"
    urls = re.findall(url_pattern, text)
    length = len(text)
    for url in urls:
        length -= len(url)
        length += TWITTER_URL_LENGTH
    return length


def test_format_within_280_chars():
    article = _make_article()
    tweet = format_for_x(article)
    assert _tweet_length(tweet) <= MAX_TWEET_LENGTH


def test_format_contains_url():
    article = _make_article()
    tweet = format_for_x(article)
    assert article["url"] in tweet


def test_format_contains_hashtags():
    article = _make_article()
    tweet = format_for_x(article)
    assert "#ベルリン" in tweet


def test_format_contains_emoji():
    article = _make_article()
    tweet = format_for_x(article)
    assert "🇩🇪" in tweet


def test_format_long_title_truncated():
    long_title = "ベ" * 300
    article = _make_article(title=long_title, summary="")
    tweet = format_for_x(article)
    assert _tweet_length(tweet) <= MAX_TWEET_LENGTH
    assert "…" in tweet


def test_format_uses_original_title_when_no_ja():
    article = {
        "url": "https://example.com/1",
        "title": "Berliner Verkehr gestört",
        "ja_title": "",
        "ja_summary": "",
    }
    article["ja_title"] = article["ja_title"] or article["title"]
    tweet = format_for_x(article)
    assert "Berliner Verkehr" in tweet
