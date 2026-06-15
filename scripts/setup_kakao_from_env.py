"""GitHub Actions 등 CI에서 환경변수로 kakao.json 생성."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "config" / "kakao.json"


def main() -> None:
    key = os.environ.get("KAKAO_REST_API_KEY", "").strip()
    refresh = os.environ.get("KAKAO_REFRESH_TOKEN", "").strip()
    if not key or not refresh:
        raise SystemExit("KAKAO_REST_API_KEY, KAKAO_REFRESH_TOKEN 환경변수가 필요합니다.")

    config = {
        "rest_api_key": key,
        "client_secret": os.environ.get("KAKAO_CLIENT_SECRET", "").strip(),
        "redirect_uri": os.environ.get("KAKAO_REDIRECT_URI", "http://localhost:8080/oauth"),
        "access_token": os.environ.get("KAKAO_ACCESS_TOKEN", "").strip(),
        "refresh_token": refresh,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
