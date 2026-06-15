"""다음 브리핑 주제 선택 및 상태 갱신."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOPICS_PATH = ROOT / "data" / "topics.json"
STATE_PATH = ROOT / "data" / "state.json"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_next_topic() -> dict:
    topics_data = load_json(TOPICS_PATH)
    state = load_json(STATE_PATH)
    topics = topics_data["topics"]
    if not topics:
        raise ValueError("topics.json 에 주제가 없습니다.")

    index = int(state.get("next_index", 0)) % len(topics)
    topic = topics[index]
    return {"index": index, "total": len(topics), **topic}


def mark_complete(topic_id: str) -> dict:
    topics_data = load_json(TOPICS_PATH)
    state = load_json(STATE_PATH)
    topics = topics_data["topics"]
    index = int(state.get("next_index", 0)) % len(topics)

    completed = set(state.get("completed_topic_ids", []))
    completed.add(topic_id)

    state["next_index"] = (index + 1) % len(topics)
    state["last_run_at"] = datetime.now(timezone.utc).isoformat()
    state["last_topic_id"] = topic_id
    state["completed_topic_ids"] = sorted(completed)
    save_json(STATE_PATH, state)
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("next", help="다음 브리핑 주제 출력 (JSON)")

    done = sub.add_parser("complete", help="브리핑 완료 후 상태 갱신")
    done.add_argument("topic_id", help="완료한 주제 id")

    args = parser.parse_args()
    if args.cmd == "next":
        print(json.dumps(get_next_topic(), ensure_ascii=False, indent=2))
    elif args.cmd == "complete":
        state = mark_complete(args.topic_id)
        print(json.dumps({"ok": True, "state": state}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
