"""OGP Agent — 記事 URL から og:image を取得して画像バイト列を返す"""

import ipaddress
import socket
import httpx
from urllib.parse import urlparse
from bs4 import BeautifulSoup


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BerlinBiyoriBot/1.0)"
}
_TIMEOUT = 10.0

# 許可するスキーム（SSRF 対策: http/https のみ）
_ALLOWED_SCHEMES = {"http", "https"}

# プライベート・予約済みアドレス範囲（SSRF 対策）
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # loopback
    ipaddress.ip_network("10.0.0.0/8"),        # private
    ipaddress.ip_network("172.16.0.0/12"),     # private
    ipaddress.ip_network("192.168.0.0/16"),    # private
    ipaddress.ip_network("169.254.0.0/16"),    # link-local (AWS metadata 等)
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]


def _is_safe_url(url: str) -> bool:
    """URLのスキームと解決先IPがSSRF的に安全かチェックする"""
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    try:
        # DNS解決し、プライベートIP範囲に解決されないか確認
        addr_infos = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addr_infos:
            ip = ipaddress.ip_address(sockaddr[0])
            if any(ip in net for net in _PRIVATE_NETWORKS):
                return False
    except (socket.gaierror, ValueError):
        return False
    return True


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
    parsed_article = urlparse(article_url)
    if image_url.startswith("//"):
        image_url = f"{parsed_article.scheme}:{image_url}"
    elif image_url.startswith("/"):
        image_url = f"{parsed_article.scheme}://{parsed_article.netloc}{image_url}"

    # SSRF 対策: スキームとIPアドレス範囲を検証
    if not _is_safe_url(image_url):
        print(f"[ogp] 安全でない URL をスキップ: {image_url}")
        return None

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
