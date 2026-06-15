"""3개월 커리큘럼 — 다음 개념 선정 및 진도 저장."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURRICULUM_PATH = ROOT / "data" / "curriculum.json"
STATE_PATH = ROOT / "data" / "state.json"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def default_state(curriculum: dict) -> dict:
    return {
        "mode": "daily_coach",
        "curriculum_version": curriculum.get("version", 1),
        "next_index": 0,
        "cycle": 1,
        "completed_concept_ids": [],
        "last_run_at": None,
        "last_concept_id": None,
    }


def sync_state(curriculum: dict, state: dict) -> dict:
    if state.get("curriculum_version") != curriculum.get("version"):
        return default_state(curriculum)
    return state


def get_concepts(curriculum: dict) -> list[dict]:
    concepts = curriculum.get("concepts", [])
    if not concepts:
        raise ValueError("curriculum.json 에 concepts 가 없습니다.")
    return concepts


def get_next_concept() -> dict:
    curriculum = load_json(CURRICULUM_PATH)
    state = sync_state(curriculum, load_json(STATE_PATH))
    concepts = get_concepts(curriculum)
    index = int(state.get("next_index", 0))
    if index >= len(concepts):
        index = 0

    concept = concepts[index]
    return {
        "index": index,
        "total": len(concepts),
        "cycle": state.get("cycle", 1),
        "month": concept.get("month"),
        "curriculum_title": curriculum.get("title"),
        "user_focus": curriculum.get("user_focus", []),
        "learning_path": curriculum.get("path", ""),
        **concept,
    }


def mark_complete(concept_id: str) -> dict:
    curriculum = load_json(CURRICULUM_PATH)
    state = sync_state(curriculum, load_json(STATE_PATH))
    concepts = get_concepts(curriculum)
    index = int(state.get("next_index", 0))

    completed = set(state.get("completed_concept_ids", []))
    completed.add(concept_id)

    state["next_index"] = (index + 1) % len(concepts)
    if index + 1 >= len(concepts):
        state["cycle"] = int(state.get("cycle", 1)) + 1
        state["next_index"] = 0

    state["completed_concept_ids"] = sorted(completed)
    state["last_run_at"] = datetime.now(timezone.utc).isoformat()
    state["last_concept_id"] = concept_id
    save_json(STATE_PATH, state)
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("next")
    done = sub.add_parser("complete")
    done.add_argument("concept_id")
    args = parser.parse_args()

    if args.cmd == "next":
        print(json.dumps(get_next_concept(), ensure_ascii=False, indent=2))
    elif args.cmd == "complete":
        state = mark_complete(args.concept_id)
        print(json.dumps({"ok": True, "state": state}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
