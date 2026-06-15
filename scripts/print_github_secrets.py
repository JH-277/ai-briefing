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
    print("필수:")
    print("  BRIEFING_CHANNEL = telegram")
    print("  GEMINI_API_KEY   = Google AI Studio API 키")
    print("  TELEGRAM_BOT_TOKEN")
    print("  TELEGRAM_CHAT_ID\n")
    print("선택:")
    print("  GEMINI_MODEL = gemini-2.0-flash (기본값)\n")

    gm = ROOT / "config" / "gemini.json"
    if gm.exists():
        g = json.loads(gm.read_text(encoding="utf-8"))
        print("Gemini (로컬 config/gemini.json):")
        print(f"  GEMINI_API_KEY = {mask(g.get('api_key', ''))}")
        print(f"  GEMINI_MODEL   = {g.get('model', 'gemini-2.0-flash')}\n")

    tg = ROOT / "config" / "telegram.json"
    if tg.exists():
        t = json.loads(tg.read_text(encoding="utf-8"))
        print("Telegram:")
        print(f"  TELEGRAM_BOT_TOKEN = {mask(t.get('bot_token', ''))}")
        print(f"  TELEGRAM_CHAT_ID   = {t.get('chat_id') or '(get_telegram_chat_id.py)'}\n")

    print("config/*.json 은 GitHub에 올리지 마세요.")


if __name__ == "__main__":
    main()
