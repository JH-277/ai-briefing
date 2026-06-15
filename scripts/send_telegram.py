"""텔레그램 Bot API로 브리핑 전송 (GitHub Actions 친화적)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "telegram.json"
API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_LEN = 4096


def load_config() -> dict:
    if CONFIG.exists():
        with CONFIG.open(encoding="utf-8") as f:
            return json.load(f)
    token = __import__("os").environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = __import__("os").environ.get("TELEGRAM_CHAT_ID", "").strip()
    if token and chat_id:
        return {"bot_token": token, "chat_id": chat_id}
    raise FileNotFoundError(
        "config/telegram.json 또는 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 필요"
    )


def extract_body(raw: str) -> str:
    marker = "## 카카오 요약"
    if marker in raw:
        part = raw.split(marker, 1)[1].strip()
        if "\n## " in part:
            part = part.split("\n## ", 1)[0].strip()
        return part
    return raw.strip()


def chunk_text(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    while text:
        chunks.append(text[:max_len])
        text = text[max_len:]
    return chunks


def send_message(token: str, chat_id: str, text: str) -> None:
    url = API.format(token=token)
    for part in chunk_text(text, MAX_LEN):
        r = requests.post(
            url,
            json={"chat_id": chat_id, "text": part},
            timeout=30,
        )
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram 전송 실패: {data}")


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text")
    group.add_argument("--file")
    parser.add_argument("--title", default="AI 개념 브리핑")
    args = parser.parse_args()

    cfg = load_config()
    token, chat_id = cfg["bot_token"], str(cfg["chat_id"])

    if args.file:
        path = Path(args.file)
        if not path.is_absolute():
            path = ROOT / path
        body = extract_body(path.read_text(encoding="utf-8"))
    else:
        body = args.text or ""

    header = f"📌 {args.title}\n\n"
    if body.startswith("📌"):
        message = body
    else:
        message = header + body
    send_message(token, chat_id, message)
    print("Telegram 전송 완료")


if __name__ == "__main__":
    main()
