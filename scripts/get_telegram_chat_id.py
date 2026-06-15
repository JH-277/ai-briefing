"""봇과 대화 후 chat_id 확인 (@BotFather 로 봇 생성 후 실행)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "config" / "telegram.example.json"
CONFIG = ROOT / "config" / "telegram.json"


def main() -> None:
    if not CONFIG.exists():
        if EXAMPLE.exists():
            CONFIG.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"생성: {CONFIG}")
            print("bot_token 을 @BotFather 에서 받은 값으로 수정하세요.")
            sys.exit(0)

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    token = cfg.get("bot_token", "").strip()
    if not token or token == "YOUR_BOT_TOKEN":
        print("config/telegram.json 에 bot_token 을 넣으세요.")
        sys.exit(1)

    print("\n1. 텔레그램에서 만든 봇에게 /start 또는 아무 메시지 전송")
    print("2. Enter 누르면 chat_id 를 조회합니다.\n")
    input("준비되면 Enter...")

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    r = requests.get(url, timeout=30)
    data = r.json()
    if not data.get("ok"):
        print("조회 실패:", data)
        sys.exit(1)

    updates = data.get("result", [])
    if not updates:
        print("메시지 없음. 봇에게 /start 를 보낸 뒤 다시 실행하세요.")
        sys.exit(1)

    chat_id = updates[-1]["message"]["chat"]["id"]
    cfg["chat_id"] = str(chat_id)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nchat_id 저장: {chat_id}")
    print('테스트: python scripts/send_telegram.py --text "연결 테스트"')


if __name__ == "__main__":
    main()
