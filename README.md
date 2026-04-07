# 🇩🇪 Berlin Biyori（ベルリン日和）

ベルリンのニュースを自動収集・日本語翻訳し、X / Threads に自動投稿するマルチエージェントシステム。

- X: [@berlin_biyori](https://x.com/berlin_biyori)
- GitHub: [berlin-biyori-bot](https://github.com/YOUR_USERNAME/berlin-biyori-bot)

---

## 概要

| 項目 | 内容 |
|---|---|
| コンセプト | ベルリン在住・関心のある日本語話者向けローカルニュース |
| 投稿先 | X（@berlin_biyori）/ Threads（将来対応） |
| 実行環境 | GitHub Actions（無料枠） |
| 実行頻度 | 6時間ごと（cron） |
| 翻訳エンジン | Claude API（claude-haiku-4-5） |
| パッケージ管理 | [uv](https://github.com/astral-sh/uv) |

---

## アーキテクチャ

```
GitHub Actions (cron)
        │
        ▼
Orchestrator Agent      ← タスク分配・フロー管理
        │
        ├──▶ Scraper Agent      ← RSS フィード収集（rbb24 / Berlin.de / BZ / Tagesspiegel）
        │         │
        │         ▼
        ├──▶ Translator Agent   ← Claude API で日本語翻訳
        │         │
        │         ▼
        ├──▶ Formatter Agent    ← SNS ごとの文体・絵文字・ハッシュタグ整形
        │         │
        │         ▼
        └──▶ Poster Agent       ← X API へ投稿
                  │
        Duplicate Checker ←── posted_urls.json（リポジトリ内にキャッシュ）
```

---

## ディレクトリ構成

```
berlin-biyori-bot/
├── .github/
│   └── workflows/
│       └── post.yml          # GitHub Actions cron 定義
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py       # Orchestrator Agent
│   ├── scraper.py            # Scraper Agent
│   ├── translator.py         # Translator Agent
│   ├── formatter.py          # Formatter Agent
│   └── poster.py             # Poster Agent
├── data/
│   └── posted_urls.json      # 投稿済み URL キャッシュ（Git 管理）
├── prompts/
│   └── translate.txt         # Claude への翻訳プロンプトテンプレート
├── tests/
│   ├── test_scraper.py
│   ├── test_translator.py
│   └── test_formatter.py
├── .env.example              # 環境変数サンプル
├── .gitignore
├── main.py                   # エントリーポイント
├── pyproject.toml            # uv プロジェクト設定
└── README.md
```

---

## 環境構築

### 前提条件

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) インストール済み

```bash
# uv のインストール（未導入の場合）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/YOUR_USERNAME/berlin-biyori-bot.git
cd berlin-biyori-bot

# uv でプロジェクト初期化・依存関係インストール
uv sync

# 環境変数を設定
cp .env.example .env
# .env を編集して各 API キーを入力
```

### 依存パッケージ（pyproject.toml）

```toml
[project]
name = "berlin-biyori-bot"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "anthropic>=0.40.0",       # Claude API
    "feedparser>=6.0.11",      # RSS パース
    "httpx>=0.27.0",           # HTTP クライアント
    "tweepy>=4.14.0",          # X (Twitter) API v2
    "python-dotenv>=1.0.0",    # 環境変数読み込み
    "beautifulsoup4>=4.12.0",  # HTML スクレイピング（補助）
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

---

## 環境変数

`.env.example` をコピーして `.env` を作成し、各値を設定する。

```env
# Claude API
ANTHROPIC_API_KEY=your_anthropic_api_key

# X (Twitter) API v2
X_API_KEY=your_api_key
X_API_SECRET=your_api_secret
X_ACCESS_TOKEN=your_access_token
X_ACCESS_TOKEN_SECRET=your_access_token_secret
X_BEARER_TOKEN=your_bearer_token
```

> **注意**: `.env` は `.gitignore` に追加し、絶対にリポジトリへ push しないこと。  
> GitHub Actions では `Settings > Secrets and variables > Actions` に同じキーを登録する。

---

## 各エージェントの仕様

### Scraper Agent

ベルリン特化のソースを優先して収集する。

**対象 RSS フィード**

| メディア | URL | 特徴 |
|---|---|---|
| rbb24 | `https://www.rbb24.de/aktuell/index.xml` | ベルリン・ブランデンブルク専門 |
| Berlin.de | `https://www.berlin.de/aktuelles/rss.xml` | ベルリン行政・公式情報 |
| Berliner Zeitung | `https://www.berliner-zeitung.de/feed.xml` | ベルリンローカル紙 |
| Tagesspiegel | `https://www.tagesspiegel.de/feed.rss` | ベルリン発・全国区 |
| Tagesschau | `https://www.tagesschau.de/xml/rss2/` | ドイツ全国（補助） |

**出力フォーマット**

```python
{
    "url": "https://...",
    "title": "記事タイトル（独語）",
    "summary": "本文要約（独語・最大500字）",
    "published": "2026-04-07T10:00:00Z",
    "source": "rbb24"
}
```

### Translator Agent

Claude API（`claude-haiku-4-5`）を使用。コスト最小化のため haiku を選択。

**翻訳プロンプト方針**

- ベルリン在住の日本語話者に向けた自然な日本語
- 固有名詞（地名・路線名・機関名）はドイツ語原文を括弧内に併記
- 翻訳調にならず、日本語ニュースとして読めるトーンを維持
- 生活に直結する情報（交通・行政・天気・イベント）は特に平易に

### Formatter Agent

**X フォーマット仕様**

| 項目 | 内容 |
|---|---|
| 文字数 | 280字以内 |
| 絵文字 | 1〜2個（冒頭に 🇩🇪 または 📰） |
| ハッシュタグ | `#ベルリン` `#ドイツ生活` `#berlin` から 2〜3個 |
| 末尾 | 元記事 URL を必ず添付 |

### Poster Agent

- X: Tweepy（API v2）で投稿
- 投稿成功後、`data/posted_urls.json` に URL を追記して Git commit

### Duplicate Checker

`data/posted_urls.json` に投稿済み URL を配列で保存。Scraper が収集した記事と突合し、既出 URL をスキップする。

```json
{
  "posted": [
    "https://www.rbb24.de/...",
    "https://www.berlin.de/..."
  ],
  "last_updated": "2026-04-07T10:00:00Z"
}
```

---

## GitHub Actions 設定

`.github/workflows/post.yml`

```yaml
name: Berlin Biyori - Post News

on:
  schedule:
    - cron: '0 */6 * * *'   # 6時間ごと（UTC）
  workflow_dispatch:          # 手動実行も可能

jobs:
  post:
    runs-on: ubuntu-latest
    permissions:
      contents: write         # posted_urls.json の commit に必要

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync

      - name: Run bot
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          X_API_KEY: ${{ secrets.X_API_KEY }}
          X_API_SECRET: ${{ secrets.X_API_SECRET }}
          X_ACCESS_TOKEN: ${{ secrets.X_ACCESS_TOKEN }}
          X_ACCESS_TOKEN_SECRET: ${{ secrets.X_ACCESS_TOKEN_SECRET }}
          X_BEARER_TOKEN: ${{ secrets.X_BEARER_TOKEN }}
        run: uv run python main.py

      - name: Commit updated cache
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/posted_urls.json
          git diff --staged --quiet || git commit -m "chore: update posted_urls cache"
          git push
```

---

## 開発・ローカル実行

```bash
# 全エージェントを実行（実際に投稿される）
uv run python main.py

# Scraper のみテスト（投稿なし）
uv run python main.py --dry-run --agent scraper

# 翻訳のみテスト
uv run python main.py --dry-run --agent translator

# テスト実行
uv run pytest tests/
```

---

## コスト試算

| 項目 | 単価 | 月間想定 | 月額 |
|---|---|---|---|
| Claude Haiku（翻訳） | $0.001 / 記事 | 〜120 本 | 〜$0.12 |
| GitHub Actions | 無料枠 2,000 分/月 | 〜60 分 | $0 |
| X API（Free プラン） | 無料（月 1,500 投稿まで） | 〜120 本 | $0 |
| **合計** | | | **〜$0.12 / 月** |

---

## 今後の拡張候補

- [ ] Threads 対応（Meta Graph API）
- [ ] Instagram 対応（ビジネスアカウント要）
- [ ] Bluesky 対応（AT Protocol）
- [ ] カテゴリ別投稿（交通・行政・イベント・天気）
- [ ] 週次まとめ投稿機能
- [ ] OGP 画像生成・添付

---

## アカウント情報

| 項目 | 内容 |
|---|---|
| Google | berlin.biyori@gmail.com |
| X | [@berlin_biyori](https://x.com/berlin_biyori) |
| GitHub | berlin-biyori-bot |

---

## ライセンス

MIT