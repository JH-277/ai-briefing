"""Gemini API로 AI Daily Coach 브리핑 생성."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "prompts" / "daily_coach.md"
BRIEFINGS = ROOT / "briefings"
CONFIG = ROOT / "config" / "gemini.json"
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}

# 무료 한도가 넉넉한 모델부터 시도 (429 시 다음 모델)
MODEL_FALLBACKS = [
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash-8b",
]


def load_gemini_config() -> dict:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "").strip()
    if CONFIG.exists():
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        key = key or cfg.get("api_key", "").strip()
        model = model or cfg.get("model", "").strip()
    if not key or key == "YOUR_GEMINI_API_KEY":
        raise SystemExit(
            "GEMINI_API_KEY 필요 — Google AI Studio에서 발급 후 "
            "config/gemini.json 또는 GitHub Secrets에 등록"
        )
    preferred = model or MODEL_FALLBACKS[0]
    models = [preferred] + [m for m in MODEL_FALLBACKS if m != preferred]
    return {"api_key": key, "models": models}


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


def format_news_block(items: list[dict]) -> str:
    if not items:
        return "(수집된 RSS 없음)"
    lines = []
    for i, item in enumerate(items[:6], 1):
        lines.append(
            f"{i}. [{item.get('source')}] {item.get('title')}\n"
            f"   link: {item.get('link')}\n"
            f"   snippet: {item.get('snippet', '')}"
        )
    return "\n".join(lines)


def build_prompt(concept: dict, news_items: list[dict], today: str) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    keywords = ", ".join(concept.get("keywords", []))
    return template.format(
        date=today,
        month=concept.get("month", 1),
        cycle=concept.get("cycle", 1),
        concept_title=concept.get("title", ""),
        keywords=keywords,
        learning_path=concept.get("learning_path", ""),
        news_block=format_news_block(news_items),
    )


def _parse_gemini_response(data: dict) -> str:
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Gemini 응답 파싱 실패: {data}") from exc


def _is_quota_error(status: int, data: dict) -> bool:
    if status == 429:
        return True
    err = data.get("error", {})
    return err.get("status") == "RESOURCE_EXHAUSTED" or err.get("code") == 429


def call_gemini_once(api_key: str, model: str, prompt: str) -> tuple[str, dict]:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048,
        },
    }
    r = requests.post(url, json=body, timeout=120)
    data = r.json()
    if not r.ok:
        return "", {"status": r.status_code, "data": data, "quota": _is_quota_error(r.status_code, data)}
    return _parse_gemini_response(data), {"status": 200, "data": data, "quota": False}


def call_gemini_with_fallback(api_key: str, models: list[str], prompt: str) -> tuple[str, str]:
    errors: list[str] = []
    for model in models:
        for attempt in range(2):
            text, info = call_gemini_once(api_key, model, prompt)
            if text:
                print(f"Gemini 성공: model={model}", file=sys.stderr)
                return text, model
            err = info["data"]
            msg = err.get("error", {}).get("message", str(err))[:200]
            errors.append(f"{model}: {msg}")
            if info.get("quota") and attempt == 0:
                print(f"Gemini quota/retry: {model}, 35s 대기...", file=sys.stderr)
                time.sleep(35)
                continue
            break
    raise RuntimeError(
        "Gemini API 전 모델 실패 (429=무료 한도). 시도: "
        + " | ".join(errors[-3:])
    )


def generate_briefing(today: str | None = None) -> dict:
    today = today or date.today().isoformat()
    concept = json.loads(run_script("curriculum_manager.py", "next"))
    news_payload = json.loads(run_script("fetch_ai_news.py", "--limit", "6"))
    news_items = news_payload.get("items", [])

    cfg = load_gemini_config()
    prompt = build_prompt(concept, news_items, today)
    body, model_used = call_gemini_with_fallback(cfg["api_key"], cfg["models"], prompt)

    BRIEFINGS.mkdir(parents=True, exist_ok=True)
    concept_id = concept["id"]
    archive = BRIEFINGS / f"daily-{today}-{concept_id}.md"
    archive.write_text(body, encoding="utf-8")

    return {
        "ok": True,
        "date": today,
        "concept_id": concept_id,
        "title": concept["title"],
        "archive": str(archive.relative_to(ROOT)),
        "news_count": len(news_items),
        "model": model_used,
    }


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="YYYY-MM-DD (테스트용)")
    args = parser.parse_args()
    meta = generate_briefing(args.date)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
