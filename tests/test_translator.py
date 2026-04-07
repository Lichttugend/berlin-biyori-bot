"""Translator Agent のテスト"""

from unittest.mock import MagicMock, patch
import pytest
from agents.translator import translate_article


def _make_article():
    return {
        "url": "https://example.com/1",
        "title": "Berliner Verkehr gestört",
        "summary": "Der Verkehr in Berlin ist heute stark beeinträchtigt.",
        "published": "2026-04-07T10:00:00+00:00",
        "source": "rbb24",
    }


def test_translate_article_success():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"title": "ベルリンの交通が混乱", "summary": "本日ベルリンの交通は大幅に乱れています。"}')]

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("agents.translator.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.return_value = mock_response
            result = translate_article(_make_article())

    assert result["ja_title"] == "ベルリンの交通が混乱"
    assert result["ja_summary"] == "本日ベルリンの交通は大幅に乱れています。"


def test_translate_article_fallback_on_error():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
        with patch("agents.translator.anthropic.Anthropic") as MockClient:
            MockClient.return_value.messages.create.side_effect = Exception("API error")
            result = translate_article(_make_article())

    # フォールバック: 元タイトルをそのまま使う
    assert result["ja_title"] == "Berliner Verkehr gestört"
    assert result["ja_summary"] == ""
