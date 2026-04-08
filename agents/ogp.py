"""OGP Agent — 記事 URL から og:image を取得して画像バイト列を返す"""

import httpx
from bs4 import BeautifulSoup


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BerlinBiyoriBot/1.0)"
}
_TIMEOUT = 10.0


def fetch_ogp_image(article_url: str) -> bytes | None:
    """記事 URL から og:image を取得し、画像バイト列を返す。取得失敗時は None。"""
    image_url = _extract_og_image_url(article_url)
    if not image_url:
        return None
    return _download_image(image_url)


def _extract_og_image_url(article_url: str) -> str | None:
    try:
        resp = httpx.get(article_url, headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ogp] ページ取得失敗 ({article_url}): {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
    if not tag:
        print(f"[ogp] og:image タグなし: {article_url}")
        return None

    image_url = tag.get("content", "").strip()
    if not image_url:
        return None

    # 相対 URL を絶対 URL に変換
    if image_url.startswith("//"):
        image_url = "https:" + image_url
    elif image_url.startswith("/"):
        from urllib.parse import urlparse
        parsed = urlparse(article_url)
        image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"

    return image_url


def _download_image(image_url: str) -> bytes | None:
    try:
        resp = httpx.get(image_url, headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            print(f"[ogp] 画像以外のコンテンツ ({content_type}): {image_url}")
            return None
        return resp.content
    except Exception as e:
        print(f"[ogp] 画像ダウンロード失敗 ({image_url}): {e}")
        return None
