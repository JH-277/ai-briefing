"""AI 관련 RSS 수집 — 관심 주제(AX·Agent·거버넌스·트렌드) 기준으로 우선순위 정렬."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent

# 글로벌·기업·거버넌스·Agent 중심 (미국 소비자 IT 비중 축소)
FEEDS: list[tuple[str, int]] = [
    ("VentureBeat AI", 3, "https://venturebeat.com/category/ai/feed/"),
    ("MIT Tech Review AI", 3, "https://www.technologyreview.com/topic/artificial-intelligence/feed/"),
    ("OpenAI News", 2, "https://openai.com/news/rss.xml"),
    ("The Register AI", 2, "https://www.theregister.com/tag/ai/atom/"),
    ("Google AI Blog", 2, "https://blog.google/technology/ai/rss/"),
    ("TechCrunch AI", 1, "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("ZDNet AI", 2, "https://www.zdnet.com/topic/artificial-intelligence/rss.xml"),
]

MAX_AGE_DAYS = 7
TIMEOUT = 20

# 관심 주제 — 매칭 시 가점
INTEREST_HIGH = [
    "agent", "agents", "mcp", "rag", "retrieval", "llm", "large language",
    "enterprise", "workplace", "automation", "workflow", "copilot",
    "governance", "regulation", "regulatory", "compliance", "eu ai act",
    "safety", "responsible ai", "ethics", "trustworthy", "audit",
    "ax", "digital transformation", "productivity", "business",
    "finance", "financial", "accounting", "erp", "sap", "enterprise ai",
    "multimodal", "reasoning", "tool use", "orchestrat",
]

INTEREST_MED = [
    "open source", "open-source", "api", "model", "inference", "training",
    "benchmark", "benchmarks", "deployment", "cloud", "microsoft", "google",
    "anthropic", "meta", "ibm", "oracle", "salesforce",
    "policy", "workforce", "jobs", "skills", "non-technical", "beginner",
]

# 소비자·엔터테인먼트 위주 — 감점
INTEREST_LOW = [
    "iphone", "android phone", "gaming", "game", "celebrity", "movie",
    "tv show", "dating app", "crypto meme", "nft", "meme coin",
    "smart speaker", "smart home gadget", "wearable", "headphone",
]

DEFAULT_USER_FOCUS = [
    "재무·회계·결산·경영지원",
    "SAP·전표·KPI·보고서",
    "AI Agent·MCP·RAG·LLM",
    "기업 AX·업무혁신",
]


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def parse_atom(xml_text: str, source: str) -> list[dict]:
    items: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    for entry in root.iter(f"{ns}entry"):
        title = strip_html(entry.findtext(f"{ns}title", ""))
        link_el = entry.find(f"{ns}link")
        link = ""
        if link_el is not None:
            link = (link_el.get("href") or link_el.text or "").strip()
        if not link:
            link = (entry.findtext(f"{ns}link") or "").strip()
        pub = entry.findtext(f"{ns}updated") or entry.findtext(f"{ns}published", "")
        summary = strip_html(
            entry.findtext(f"{ns}summary") or entry.findtext(f"{ns}content", "")
        )[:280]
        if not title:
            continue
        published = _parse_date(pub)
        items.append(
            {
                "source": source,
                "title": title,
                "link": link,
                "snippet": summary,
                "published": published.isoformat() if published else None,
            }
        )
    return items


def parse_rss(xml_text: str, source: str) -> list[dict]:
    items: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    channel = root.find("channel")
    nodes = channel.findall("item") if channel is not None else root.iter("item")

    for item in nodes:
        title = strip_html(item.findtext("title", ""))
        link = (item.findtext("link") or "").strip()
        pub = item.findtext("pubDate", "") or item.findtext("published", "")
        desc = strip_html(
            item.findtext("description", "") or item.findtext("summary", "")
        )[:280]
        if not title:
            continue
        published = _parse_date(pub)
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


def _parse_date(pub: str) -> datetime | None:
    if not pub:
        return None
    try:
        return parsedate_to_datetime(pub).astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        return datetime.fromisoformat(pub.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def parse_feed(xml_text: str, source: str) -> list[dict]:
    text = xml_text.lstrip()
    if text.startswith("<feed") or ":feed" in text[:120]:
        return parse_atom(xml_text, source)
    return parse_rss(xml_text, source)


def is_recent(item: dict) -> bool:
    if not item.get("published"):
        return True
    try:
        published = datetime.fromisoformat(item["published"])
        age = datetime.now(timezone.utc) - published
        return age.days <= MAX_AGE_DAYS
    except ValueError:
        return True


def _tokenize_focus(text: str) -> list[str]:
    parts = re.split(r"[,·/|]+", text.lower())
    tokens: list[str] = []
    for part in parts:
        part = part.strip()
        if len(part) >= 2:
            tokens.append(part)
    return tokens


def _contains_term(text: str, term: str) -> bool:
    term = term.strip().lower()
    if not term:
        return False
    if " " in term or "-" in term or len(term) >= 5:
        return term in text
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None


def score_item(
    item: dict,
    source_weight: int,
    concept_keywords: list[str],
    user_focus: list[str],
) -> tuple[int, list[str]]:
    text = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
    score = source_weight
    reasons: list[str] = []

    for kw in INTEREST_HIGH:
        if _contains_term(text, kw):
            score += 3
            reasons.append(kw)

    for kw in INTEREST_MED:
        if _contains_term(text, kw):
            score += 1
            reasons.append(kw)

    for kw in INTEREST_LOW:
        if _contains_term(text, kw):
            score -= 4

    for kw in concept_keywords:
        k = kw.lower().strip()
        if len(k) >= 2 and _contains_term(text, k):
            score += 5
            reasons.append(f"concept:{kw}")

    for focus in user_focus:
        for token in _tokenize_focus(focus):
            if len(token) >= 2 and _contains_term(text, token):
                score += 2
                reasons.append(f"focus:{token}")

    # 중복 reason 정리 (표시용 상위 3개)
    seen: set[str] = set()
    unique_reasons: list[str] = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            unique_reasons.append(r)

    return score, unique_reasons[:4]


def fetch_news(
    limit: int = 8,
    concept_keywords: list[str] | None = None,
    user_focus: list[str] | None = None,
) -> list[dict]:
    concept_keywords = concept_keywords or []
    user_focus = user_focus or DEFAULT_USER_FOCUS

    collected: list[dict] = []
    seen: set[str] = set()

    for source, weight, url in FEEDS:
        try:
            r = requests.get(
                url,
                timeout=TIMEOUT,
                headers={"User-Agent": "AI-Daily-Coach/1.0"},
            )
            r.raise_for_status()
        except requests.RequestException as exc:
            print(f"RSS skip {source}: {exc}", file=sys.stderr)
            continue

        for item in parse_feed(r.text, source):
            key = item.get("link") or item.get("title", "")
            if not key or key in seen or not is_recent(item):
                continue
            seen.add(key)
            relevance, tags = score_item(item, weight, concept_keywords, user_focus)
            item["relevance_score"] = relevance
            item["relevance_tags"] = tags
            collected.append(item)

    collected.sort(
        key=lambda x: (x.get("relevance_score", 0), x.get("published") or ""),
        reverse=True,
    )
    return collected[:limit]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument(
        "--concept-keywords",
        default="",
        help="쉼표 구분 — 오늘 커리큘럼 키워드",
    )
    parser.add_argument(
        "--user-focus",
        default="",
        help='JSON 배열 또는 쉼표 구분 — 독자 관심사',
    )
    parser.add_argument("--out", type=Path, help="JSON 저장 경로")
    args = parser.parse_args()

    concept_keywords = [k.strip() for k in args.concept_keywords.split(",") if k.strip()]
    user_focus = DEFAULT_USER_FOCUS
    if args.user_focus.strip():
        raw = args.user_focus.strip()
        if raw.startswith("["):
            user_focus = json.loads(raw)
        else:
            user_focus = [x.strip() for x in raw.split(",") if x.strip()]

    news = fetch_news(
        limit=args.limit,
        concept_keywords=concept_keywords,
        user_focus=user_focus,
    )
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "selection": "relevance_ranked",
        "items": news,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
