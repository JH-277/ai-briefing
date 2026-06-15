"""Gemini 생성 → Telegram/Kakao 전송 → 커리큘럼 진도 갱신."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "config" / "settings.json"
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def run_script(name: str, *args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / name), *args],
        cwd=ROOT,
        capture_output=True,
        env=ENV,
    )
    stdout = (result.stdout or b"").decode("utf-8", errors="replace")
    stderr = (result.stderr or b"").decode("utf-8", errors="replace")
    if result.returncode != 0:
        print(stderr or stdout, file=sys.stderr)
        raise SystemExit(result.returncode)
    return stdout


def delivery_channel() -> str:
    if os.environ.get("BRIEFING_CHANNEL"):
        return os.environ["BRIEFING_CHANNEL"].strip().lower()
    if SETTINGS.exists():
        data = json.loads(SETTINGS.read_text(encoding="utf-8"))
        return data.get("delivery_channel", "telegram").lower()
    return "telegram"


def send_briefing(archive_rel: str, title: str, channel: str) -> None:
    if channel in ("telegram", "both"):
        run_script(
            "send_telegram.py",
            "--file",
            archive_rel,
            "--title",
            f"AI Daily Coach — {title}",
        )
    if channel in ("kakao", "both"):
        run_script(
            "send_kakao.py",
            "--file",
            archive_rel,
            "--title",
            f"AI Daily Coach — {title}",
        )


def main() -> None:
    channel = delivery_channel()
    meta = json.loads(run_script("generate_daily_briefing.py"))
    concept_id = meta["concept_id"]
    title = meta["title"]
    archive = meta["archive"]

    send_briefing(archive, title, channel)
    run_script("curriculum_manager.py", "complete", concept_id)

    print(
        json.dumps(
            {
                "ok": True,
                "mode": "daily_coach",
                "concept_id": concept_id,
                "title": title,
                "channel": channel,
                "archive": archive,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
