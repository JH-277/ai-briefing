"""Gemini API로 AI Daily Coach 브리핑 생성 (실패 시 오프라인 fallback)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

KST = timezone(timedelta(hours=9))

ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = ROOT / "prompts" / "daily_coach.md"
LIBRARY = ROOT / "content" / "library"
BRIEFINGS = ROOT / "briefings"
CONFIG = ROOT / "config" / "gemini.json"
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}

MODEL_FALLBACKS = [
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
]
GROQ_MODEL = "llama-3.3-70b-versatile"


def today_kst() -> str:
    return datetime.now(KST).date().isoformat()


def load_gemini_config() -> dict | None:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    model = os.environ.get("GEMINI_MODEL", "").strip()
    if CONFIG.exists():
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        key = key or cfg.get("api_key", "").strip()
        model = model or cfg.get("model", "").strip()
    if not key or key == "YOUR_GEMINI_API_KEY":
        return None
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
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048},
    }
    r = requests.post(url, json=body, timeout=120)
    data = r.json()
    if not r.ok:
        return "", {
            "status": r.status_code,
            "data": data,
            "quota": _is_quota_error(r.status_code, data),
        }
    return _parse_gemini_response(data), {"status": 200, "data": data, "quota": False}


def call_gemini_with_fallback(api_key: str, models: list[str], prompt: str) -> tuple[str, str]:
    errors: list[str] = []
    for model in models:
        text, info = call_gemini_once(api_key, model, prompt)
        if text:
            print(f"Gemini 성공: model={model}", file=sys.stderr)
            return text, model
        msg = info["data"].get("error", {}).get("message", str(info["data"]))[:160]
        errors.append(f"{model}: {msg}")
        if info.get("quota"):
            print(f"Gemini quota: {model}, 다음 모델 시도...", file=sys.stderr)
    raise RuntimeError("Gemini 전 모델 실패: " + " | ".join(errors))


def load_groq_key() -> str:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    groq_cfg = ROOT / "config" / "groq.json"
    if groq_cfg.exists():
        key = key or json.loads(groq_cfg.read_text(encoding="utf-8")).get("api_key", "").strip()
    return key


def call_groq(api_key: str, prompt: str) -> str:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,
            "temperature": 0.7,
        },
        timeout=120,
    )
    data = r.json()
    if not r.ok:
        raise RuntimeError(f"Groq API 오류: {data}")
    return data["choices"][0]["message"]["content"].strip()


def _library_excerpt(concept_id: str) -> str:
    legacy_map = {
        "m1-llm-basics": "chatgpt-vs-work",
        "m2-rag-basics": "meeting-rag",
        "m2-agent-basics": "agent-hype",
        "m3-mcp-basics": "api-mcp-daily",
    }
    path = LIBRARY / f"{legacy_map.get(concept_id, '')}.md"
    if not path.exists():
        return ""
    raw = path.read_text(encoding="utf-8")
    marker = "## 카카오 요약"
    if marker in raw:
        return raw.split(marker, 1)[1].strip()[:400]
    return raw[:400]


def generate_offline_briefing(concept: dict, news_items: list[dict], today: str) -> str:
    title = concept.get("title", "")
    keywords = ", ".join(concept.get("keywords", []))
    month = concept.get("month", 1)
    cycle = concept.get("cycle", 1)
    concept_id = concept.get("id", "")

    news_lines = []
    for i, item in enumerate(news_items[:2], 1):
        news_lines.append(f"{i}. {item.get('title', '')}\n   {item.get('link', '')}")
    news_sec = "\n".join(news_lines) if news_lines else "오늘 RSS 수집 없음 — 개념·실무에 집중"

    extra = _library_excerpt(concept_id)
    extra_block = f"\n\n💡 참고:\n{extra}" if extra else ""

    return f"""📌 AI Daily Coach · {today}

⚠️ Gemini API 무료 한도 초과 → 오늘은 간이 브리핑입니다. (한도 복구 시 AI 풀 버전 자동 재개)

🔹 오늘의 AI 뉴스 (2건)
{news_sec}

🔹 오늘의 AI 개념: {title}
• 키워드: {keywords}
• {month}개월차 · {cycle}회독
• 학습 경로: {concept.get('learning_path', '')}
• 오늘은 API 한도로 AI 상세 설명 대신 커리큘럼 주제를 안내합니다.{extra_block}

🔹 AX 실무 활용
재무·회계·SAP 맥락에서 '{title}'은 FAQ 검색, 결산 체크리스트, 보고서 초안에 연결해 보세요.

🔹 오늘의 Agent 아이디어
'{title}' Agent — SAP/전표·규정 PDF를 검색해 3줄 요약 후 이메일/Teams로 보내는 1단계 자동화부터."""




def generate_briefing(today: str | None = None) -> dict:
    today = today or today_kst()
    concept = json.loads(run_script("curriculum_manager.py", "next"))
    news_payload = json.loads(run_script("fetch_ai_news.py", "--limit", "6"))
    news_items = news_payload.get("items", [])

    prompt = build_prompt(concept, news_items, today)
    model_used = "offline-fallback"
    body = ""

    cfg = load_gemini_config()
    if cfg:
        try:
            body, model_used = call_gemini_with_fallback(cfg["api_key"], cfg["models"], prompt)
        except RuntimeError as exc:
            print(f"Gemini 실패: {exc}", file=sys.stderr)

    if not body:
        groq_key = load_groq_key()
        if groq_key and groq_key != "YOUR_GROQ_API_KEY":
            try:
                body = call_groq(groq_key, prompt)
                model_used = GROQ_MODEL
                print(f"Groq 성공: {GROQ_MODEL}", file=sys.stderr)
            except RuntimeError as exc:
                print(f"Groq 실패: {exc}", file=sys.stderr)

    if not body:
        print("AI 생성 실패 → offline fallback", file=sys.stderr)
        body = generate_offline_briefing(concept, news_items, today)

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
        "fallback": model_used == "offline-fallback",
        "ai_provider": (
            "groq"
            if model_used == GROQ_MODEL
            else "offline"
            if model_used == "offline-fallback"
            else "gemini"
        ),
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
