"""Formatter Agent — X 投稿用テキストを整形する"""

# X は URL を 23 文字として計算する
TWITTER_URL_LENGTH = 23
MAX_TWEET_LENGTH = 280

NEWS_HASHTAGS = "#ベルリン #ドイツ生活 #berlin"
EVENT_HASHTAGS = "#ベルリン #ベルリンイベント #berlin"
NEWS_EMOJI = "🇩🇪"
EVENT_EMOJI = "🎭"


def format_for_x(article: dict) -> str:
    """article から 280 字以内のツイート文字列を生成する"""
    title = article.get("ja_title") or article.get("title", "")
    summary = article.get("ja_summary", "")
    url = article["url"]
    is_event = article.get("content_type") == "event"

    lead_emoji = EVENT_EMOJI if is_event else NEWS_EMOJI
    hashtags = EVENT_HASHTAGS if is_event else NEWS_HASHTAGS

    # 固定部分の文字数を計算（URL は TWITTER_URL_LENGTH として扱う）
    # 構成: {emoji} {title}\n\n{summary}\n\n{hashtags}\n{url}
    fixed = f"{lead_emoji} \n\n\n\n{hashtags}\n"
    fixed_len = len(fixed) + TWITTER_URL_LENGTH

    # title + summary に使える文字数
    available = MAX_TWEET_LENGTH - fixed_len

    # title を優先し、残り文字数で summary を切り詰める
    if len(title) > available:
        title = title[: available - 1] + "…"
        summary = ""
    else:
        remaining = available - len(title)
        if summary and remaining > 4:
            # "\n\n" の 2 文字 + summary
            remaining -= 2
            if len(summary) > remaining:
                summary = summary[: remaining - 1] + "…"
        else:
            summary = ""

    parts = [f"{lead_emoji} {title}"]
    if summary:
        parts.append(summary)
    parts.append(hashtags)
    parts.append(url)

    return "\n\n".join(parts)
