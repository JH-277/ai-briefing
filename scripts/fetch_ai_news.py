"""AI 관련 RSS에서 최신 헤드라인 수집 (요약은 Gemini가 수행)."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent

FEEDS = [
    ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
]

MAX_AGE_DAYS = 7
TIMEOUT = 20


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def parse_rss(xml_text: str, source: str) -> list[dict]:
    items: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    for item in root.iter("item"):
        title = strip_html(item.findtext("title", ""))
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate", "")
        desc = strip_html(item.findtext("description", ""))[:280]
        if not title or not link:
            continue
        published = None
        if pub:
            try:
                published = parsedate_to_datetime(pub).astimezone(timezone.utc)
            except (TypeError, ValueError, OverflowError):
                published = None
        items.append(
            {
                "source": source,
                "title": title,
                "link": link,
                "snippet": desc,
                "published": published.isoformat() if published else None,
            }
        )
    return items


def is_recent(item: dict) -> bool:
    if not item.get("published"):
        return True
    try:
        published = datetime.fromisoformat(item["published"])
        age = datetime.now(timezone.utc) - published
        return age.days <= MAX_AGE_DAYS
    except ValueError:
        return True


def fetch_news(limit: int = 6) -> list[dict]:
    collected: list[dict] = []
    seen: set[str] = set()

    for source, url in FEEDS:
        try:
            r = requests.get(
                url,
                timeout=TIMEOUT,
                headers={"User-Agent": "AI-Daily-Coach/1.0"},
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            print(f"RSS skip {source}: {exc}")
            continue

        for item in parse_rss(r.text, source):
            key = item["link"] or item["title"]
            if key in seen or not is_recent(item):
                continue
            seen.add(key)
            collected.append(item)

    collected.sort(key=lambda x: x.get("published") or "", reverse=True)
    return collected[:limit]


def main() -> None:
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--out", type=Path, help="JSON 저장 경로")
    args = parser.parse_args()

    news = fetch_news(limit=args.limit)
    payload = {"fetched_at": datetime.now(timezone.utc).isoformat(), "items": news}
    text = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
