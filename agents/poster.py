"""Poster Agent — X (Twitter) API v2 へ投稿し、投稿済み URL を記録する"""

import io
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import tweepy
import requests
from requests_oauthlib import OAuth1Session

POSTED_URLS_PATH = Path(__file__).parent.parent / "data" / "posted_urls.json"
URL_TTL_DAYS = 30


def _load_posted_data() -> dict:
    if not POSTED_URLS_PATH.exists():
        return {"posted": {}, "last_updated": ""}
    data = json.loads(POSTED_URLS_PATH.read_text(encoding="utf-8"))
    # 旧フォーマット（list）を新フォーマット（dict）に移行
    if isinstance(data.get("posted"), list):
        now = datetime.now(timezone.utc).isoformat()
        data["posted"] = {url: now for url in data["posted"]}
    return data


def _save_posted_data(data: dict) -> None:
    POSTED_URLS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_posted_urls() -> set[str]:
    data = _load_posted_data()
    cutoff = datetime.now(timezone.utc) - timedelta(days=URL_TTL_DAYS)
    active = {}
    for url, ts in data.get("posted", {}).items():
        try:
            if datetime.fromisoformat(ts) >= cutoff:
                active[url] = ts
        except (ValueError, TypeError):
            active[url] = ts  # パース不能なものはそのまま残す
    if len(active) != len(data.get("posted", {})):
        expired = len(data.get("posted", {})) - len(active)
        print(f"[poster] {expired} 件の期限切れURLを削除")
        data["posted"] = active
        _save_posted_data(data)
    return set(active.keys())


def _get_oauth_session() -> OAuth1Session:
    """OAuth 1.0a セッションを返す（tweepy を介さず直接 requests で署名）"""
    return OAuth1Session(
        client_key=os.environ["X_API_KEY"],
        client_secret=os.environ["X_API_SECRET"],
        resource_owner_key=os.environ["X_ACCESS_TOKEN"],
        resource_owner_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
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


def _create_tweet(text: str, media_ids: list | None = None) -> str:
    """requests_oauthlib で直接 POST /2/tweets を呼ぶ。tweet_id を返す。"""
    oauth = _get_oauth_session()
    payload: dict = {"text": text}
    if media_ids:
        payload["media"] = {"media_ids": media_ids}
    r = oauth.post("https://api.twitter.com/2/tweets", json=payload)
    if r.status_code == 201:
        return r.json()["data"]["id"]
    raise Exception(f"{r.status_code} {r.text}")


def post_tweet(text: str, url: str, image_bytes: bytes | None = None, dry_run: bool = False) -> bool:
    """ツイートを投稿し、成功したら URL を記録して True を返す"""
    if dry_run:
        has_image = image_bytes is not None
        print(f"[poster] DRY RUN — 投稿スキップ (画像あり: {has_image})\n{text}\n")
        return True

    media_ids = None
    if image_bytes:
        media_id = _upload_image(image_bytes)
        if media_id:
            media_ids = [media_id]

    # 画像ありで試みる
    for attempt, ids in enumerate([media_ids, None] if media_ids else [None, None]):
        if attempt == 1 and media_ids is None:
            break  # 最初から画像なしの場合は2回試みない
        if attempt == 1:
            print("[poster] 画像なしで再試行...")
        try:
            tweet_id = _create_tweet(text, ids)
            print(f"[poster] 投稿成功 (画像あり: {ids is not None}): https://x.com/i/web/status/{tweet_id}")
            now = datetime.now(timezone.utc).isoformat()
            data = _load_posted_data()
            data["posted"][url] = now
            data["last_updated"] = now
            _save_posted_data(data)
            return True
        except Exception as e:
            err_str = str(e)
            if "duplicate" in err_str.lower():
                print(f"[poster] 重複コンテンツのためスキップ、投稿済みとして記録: {url}")
                now = datetime.now(timezone.utc).isoformat()
                data = _load_posted_data()
                data["posted"][url] = now
                data["last_updated"] = now
                _save_posted_data(data)
                return False
            print(f"[poster] 投稿失敗 ({url}): {e}")
            if attempt == 0 and media_ids:
                continue  # 画像なしで再試行
            return False

    return False
