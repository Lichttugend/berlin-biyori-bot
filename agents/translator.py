"""Translator Agent — Claude API (claude-haiku-4-5) でドイツ語→日本語翻訳"""

import json
import os
from pathlib import Path

import anthropic

MODEL = "claude-haiku-4-5-20251001"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "translate.txt"


def _load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def translate_article(article: dict) -> dict:
    """article に ja_title / ja_summary キーを追加して返す"""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    template = _load_prompt_template()
    prompt = template.format(
        content_type=article.get("content_type", "news"),
        title=article["title"],
        summary=article["summary"] or article["title"],
    )

    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        # JSON ブロックを取り出す
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        article["ja_title"] = data.get("title", article["title"])
        article["ja_summary"] = data.get("summary", "")
    except Exception as e:
        print(f"[translator] 翻訳失敗 ({article['url']}): {e}")
        article["ja_title"] = article["title"]
        article["ja_summary"] = ""

    return article
