"""GitHub Actions에서 Telegram/Kakao config 파일 생성."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    channel = os.environ.get("BRIEFING_CHANNEL", "").strip().lower()
    if not channel:
        settings = ROOT / "config" / "settings.json"
        if settings.exists():
            channel = json.loads(settings.read_text(encoding="utf-8")).get(
                "delivery_channel", "telegram"
            )
        else:
            channel = "telegram"

    os.environ["BRIEFING_CHANNEL"] = channel
    print(f"BRIEFING_CHANNEL={channel}")

    if channel in ("telegram", "both"):
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat_id:
            print("Telegram secrets missing", file=sys.stderr)
            sys.exit(1)
        path = ROOT / "config" / "telegram.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            json.dumps({"bot_token": token, "chat_id": chat_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    if channel in ("kakao", "both"):
        key = os.environ.get("KAKAO_REST_API_KEY", "").strip()
        refresh = os.environ.get("KAKAO_REFRESH_TOKEN", "").strip()
        if not key or not refresh:
            print("Kakao secrets missing", file=sys.stderr)
            sys.exit(1)
        path = ROOT / "config" / "kakao.json"
        path.write_text(
            json.dumps(
                {
                    "rest_api_key": key,
                    "client_secret": os.environ.get("KAKAO_CLIENT_SECRET", "").strip(),
                    "redirect_uri": os.environ.get(
                        "KAKAO_REDIRECT_URI", "http://localhost:8080/oauth"
                    ),
                    "access_token": os.environ.get("KAKAO_ACCESS_TOKEN", "").strip(),
                    "refresh_token": refresh,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
