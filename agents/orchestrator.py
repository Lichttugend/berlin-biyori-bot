"""Orchestrator Agent — スクレイプ → 翻訳 → 整形 → 投稿 のフローを管理する"""

from agents.scraper import fetch_articles
from agents.translator import translate_article
from agents.formatter import format_for_x
from agents.poster import load_posted_urls, post_tweet

# 1 回の実行で最大投稿する記事数
MAX_POSTS_PER_RUN = 3


def run(dry_run: bool = False, only_agent: str | None = None) -> None:
    print(f"[orchestrator] 開始 (dry_run={dry_run}, only_agent={only_agent})")

    # --- Scraper ---
    posted_urls = load_posted_urls()
    articles = fetch_articles(posted_urls)
    print(f"[orchestrator] 新着記事: {len(articles)} 件")

    if only_agent == "scraper":
        for a in articles:
            print(f"  - [{a['source']}] {a['title']}")
            print(f"    {a['url']}")
        return

    if not articles:
        print("[orchestrator] 新着なし。終了。")
        return

    # 投稿数を制限
    articles = articles[:MAX_POSTS_PER_RUN]

    posted_count = 0
    for article in articles:
        # --- Translator ---
        article = translate_article(article)
        print(f"[orchestrator] 翻訳: {article['ja_title']}")

        if only_agent == "translator":
            print(f"  summary: {article['ja_summary']}")
            continue

        # --- Formatter ---
        tweet_text = format_for_x(article)
        print(f"[orchestrator] 整形完了 ({len(tweet_text)} 字)")

        if only_agent == "formatter":
            print(tweet_text)
            continue

        # --- Poster ---
        success = post_tweet(tweet_text, article["url"], dry_run=dry_run)
        if success:
            posted_count += 1

    print(f"[orchestrator] 完了 — 投稿: {posted_count} 件")
