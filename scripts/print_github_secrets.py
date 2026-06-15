#!/usr/bin/env python3
"""GitHub Secrets 등록용 — 값은 config 파일에서 (로컬만)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def mask(s: str, n: int = 4) -> str:
    if not s:
        return "(없음)"
    if len(s) <= n * 2:
        return "*" * len(s)
    return f"{s[:n]}...{s[-n:]}"


def main() -> None:
    print("=== GitHub → Settings → Secrets → Actions ===\n")
    print("필수 (공통):")
    print("  BRIEFING_CHANNEL = telegram  (또는 kakao / both)\n")

    tg = ROOT / "config" / "telegram.json"
    if tg.exists():
        t = json.loads(tg.read_text(encoding="utf-8"))
        print("Telegram (권장):")
        print(f"  TELEGRAM_BOT_TOKEN = {mask(t.get('bot_token', ''))}")
        print(f"  TELEGRAM_CHAT_ID   = {t.get('chat_id') or '(get_telegram_chat_id.py 실행)'}\n")

    kk = ROOT / "config" / "kakao.json"
    if kk.exists():
        k = json.loads(kk.read_text(encoding="utf-8"))
        print("Kakao (선택):")
        print(f"  KAKAO_REST_API_KEY  = {mask(k.get('rest_api_key', ''))}")
        print(f"  KAKAO_REFRESH_TOKEN = {mask(k.get('refresh_token', ''))}")
        print(f"  KAKAO_ACCESS_TOKEN  = {mask(k.get('access_token', ''))} (선택)\n")

    print("실제 값은 Secrets 입력란에 config 파일 내용을 복사하세요.")
    print("config/*.json 은 GitHub에 올리지 마세요.")


if __name__ == "__main__":
    main()
