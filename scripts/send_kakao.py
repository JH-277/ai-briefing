"""브리핑 텍스트를 카카오톡 '나에게 보내기'로 전송."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from kakao_token import get_valid_access_token, refresh_access_token, load_config  # noqa: E402

SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
SETTINGS_PATH = ROOT / "config" / "settings.json"


def load_settings() -> dict:
    with SETTINGS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def chunk_text(text: str, max_len: int) -> list[str]:
    text = text.strip()
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n"):
        block = paragraph if not current else f"{current}\n{paragraph}"
        if len(block) <= max_len:
            current = block
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(paragraph) > max_len:
            chunks.append(paragraph[:max_len])
            paragraph = paragraph[max_len:]
        current = paragraph
    if current:
        chunks.append(current)
    return chunks


def send_text_message(text: str) -> None:
    token = get_valid_access_token()
    template = {
        "object_type": "text",
        "text": text,
        "link": {
            "web_url": "https://developers.kakao.com",
            "mobile_web_url": "https://developers.kakao.com",
        },
        "button_title": "AI 개념 브리핑",
    }
    response = requests.post(
        SEND_URL,
        headers={"Authorization": f"Bearer {token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=30,
    )
    if response.status_code == 401:
        config = load_config()
        refresh_access_token(config)
        send_text_message(text)
        return
    if response.status_code != 200:
        raise RuntimeError(f"카카오 전송 실패 ({response.status_code}): {response.text}")


def extract_kakao_body(raw: str) -> str:
    marker = "## 카카오 요약"
    if marker in raw:
        part = raw.split(marker, 1)[1].strip()
        # 다음 ## 섹션 전까지만
        if "\n## " in part:
            part = part.split("\n## ", 1)[0].strip()
        return part
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description="카카오톡 나에게 브리핑 전송")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="전송할 텍스트")
    group.add_argument("--file", help="전송할 마크다운/텍스트 파일 경로")
    parser.add_argument("--title", default="AI 개념 브리핑", help="메시지 첫 줄 제목")
    args = parser.parse_args()

    settings = load_settings()
    max_len = int(settings.get("max_kakao_chars_per_message", 900))

    if args.file:
        path = Path(args.file)
        if not path.is_absolute():
            path = ROOT / path
        body = path.read_text(encoding="utf-8")
        body = extract_kakao_body(body)
    else:
        body = args.text or ""

    # 카카오 text 템플릿은 짧을수록 안전 — 긴 본문은 여러 메시지로 분할
    header = f"📌 {args.title}\n\n"
    chunks = chunk_text(header + body, max_len)

    for i, chunk in enumerate(chunks, start=1):
        prefix = f"[{i}/{len(chunks)}]\n" if len(chunks) > 1 else ""
        send_text_message(prefix + chunk)

    print(f"전송 완료 ({len(chunks)}개 메시지)")


if __name__ == "__main__":
    main()
