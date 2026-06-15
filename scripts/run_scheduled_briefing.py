"""저장된 브리핑을 순환 전송 (Telegram / Kakao / 둘 다)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "content" / "library"
BRIEFINGS = ROOT / "briefings"
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


def send_briefing(archive: Path, title: str, channel: str) -> None:
    rel = str(archive.relative_to(ROOT))
    if channel in ("telegram", "both"):
        run_script("send_telegram.py", "--file", rel, "--title", title)
    if channel in ("kakao", "both"):
        run_script("send_kakao.py", "--file", rel, "--title", title)


def main() -> None:
    channel = delivery_channel()
    topic = json.loads(run_script("topic_manager.py", "next"))
    topic_id = topic["id"]
    title = topic["title"]

    source = LIBRARY / f"{topic_id}.md"
    if not source.exists():
        raise SystemExit(f"브리핑 없음: {source}")

    today = date.today().isoformat()
    archive = BRIEFINGS / f"{topic_id}-{today}.md"
    BRIEFINGS.mkdir(parents=True, exist_ok=True)
    archive.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    send_briefing(archive, title, channel)
    run_script("topic_manager.py", "complete", topic_id)

    print(
        json.dumps(
            {"ok": True, "topic_id": topic_id, "title": title, "channel": channel},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
