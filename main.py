"""エントリーポイント"""

import argparse
from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Berlin Biyori Bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="投稿せずに動作確認のみ行う",
    )
    parser.add_argument(
        "--agent",
        choices=["scraper", "translator", "formatter"],
        help="指定したエージェントまでの処理を実行して終了",
    )
    args = parser.parse_args()

    from agents.orchestrator import run
    run(dry_run=args.dry_run, only_agent=args.agent)


if __name__ == "__main__":
    main()
