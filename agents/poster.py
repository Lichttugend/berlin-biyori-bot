"""Poster Agent — X (Twitter) API v2 へ投稿し、投稿済み URL を記録する"""

import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import tweepy

POSTED_URLS_PATH = Path(__file__).parent.parent / "data" / "posted_urls.json"


def _load_posted_data() -> dict:
    if POSTED_URLS_PATH.exists():
        return json.loads(POSTED_URLS_PATH.read_text(encoding="utf-8"))
    return {"posted": [], "last_updated": ""}


def _save_posted_data(data: dict) -> None:
    POSTED_URLS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_posted_urls() -> set[str]:
    return set(_load_posted_data().get("posted", []))


def _get_client() -> tweepy.Client:
    return tweepy.Client(
        bearer_token=os.environ["X_BEARER_TOKEN"],
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
        wait_on_rate_limit=True,
    )


def _get_api_v1() -> tweepy.API:
    """メディアアップロード用の v1.1 API クライアントを返す"""
    auth = tweepy.OAuth1UserHandler(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    return tweepy.API(auth)


def _upload_image(image_bytes: bytes) -> str | None:
    """画像バイト列を X にアップロードし media_id を返す。失敗時は None。"""
    try:
        api = _get_api_v1()
        media = api.media_upload(filename="ogp.jpg", file=io.BytesIO(image_bytes))
        print(f"[poster] 画像アップロード成功: media_id={media.media_id_string}")
        return media.media_id_string
    except Exception as e:
        print(f"[poster] 画像アップロード失敗: {e}")
        return None


def post_tweet(text: str, url: str, image_bytes: bytes | None = None, dry_run: bool = False) -> bool:
    """ツイートを投稿し、成功したら URL を記録して True を返す"""
    if dry_run:
        has_image = image_bytes is not None
        print(f"[poster] DRY RUN — 投稿スキップ (画像あり: {has_image})\n{text}\n")
        return True

    try:
        client = _get_client()

        media_ids = None
        if image_bytes:
            media_id = _upload_image(image_bytes)
            if media_id:
                media_ids = [media_id]

        response = client.create_tweet(text=text, media_ids=media_ids)
        tweet_id = response.data["id"]
        print(f"[poster] 投稿成功: https://x.com/i/web/status/{tweet_id}")

        data = _load_posted_data()
        if url not in data["posted"]:
            data["posted"].append(url)
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        _save_posted_data(data)
        return True
    except Exception as e:
        print(f"[poster] 投稿失敗 ({url}): {e}")
        return False
