"""인가 코드 또는 리다이렉트 URL로 토큰 발급 (비대화형)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from kakao_token import KAKAO_CONFIG, save_config, _with_client_secret  # noqa: E402

TOKEN_URL = "https://kauth.kakao.com/oauth/token"


def extract_code(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("http") and "code=" in raw:
        return parse_qs(urlparse(raw).query)["code"][0]
    if "code=" in raw:
        return raw.split("code=")[1].split("&")[0]
    return raw


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/kakao_finish_auth.py \"리다이렉트_URL_또는_code\"")
        sys.exit(1)

    with KAKAO_CONFIG.open(encoding="utf-8") as f:
        config = json.load(f)

    code = extract_code(sys.argv[1])
    data = _with_client_secret(
        config,
        {
            "grant_type": "authorization_code",
            "client_id": config["rest_api_key"],
            "redirect_uri": config["redirect_uri"],
            "code": code,
        },
    )
    response = requests.post(TOKEN_URL, data=data, timeout=30)
    result = response.json()
    if response.status_code != 200:
        print("토큰 발급 실패:", result)
        sys.exit(1)

    config["access_token"] = result["access_token"]
    config["refresh_token"] = result["refresh_token"]
    save_config(config)
    print("토큰 저장 완료!")


if __name__ == "__main__":
    main()
