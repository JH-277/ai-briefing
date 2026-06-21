"""Gemini/Groq 생성 → Telegram/Kakao 전송 → 커리큘럼 진도 갱신."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "config" / "settings.json"
STATE_PATH = ROOT / "data" / "state.json"
KST = timezone(timedelta(hours=9))
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def today_kst() -> str:
    return datetime.now(KST).date().isoformat()


def already_sent_today() -> bool:
    if not STATE_PATH.exists():
        return False
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    last = state.get("last_run_at")
    if not last:
        return False
    last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
    return last_dt.astimezone(KST).date().isoformat() == today_kst()


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
    if already_sent_today():
        print(
            json.dumps(
                {"ok": True, "skipped": True, "reason": "already_sent_today_kst"},
                ensure_ascii=False,
            )
        )
        return

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
                "ai_provider": meta.get("ai_provider"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
