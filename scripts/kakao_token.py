"""카카오 OAuth 토큰 로드·저장·갱신."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
KAKAO_CONFIG = ROOT / "config" / "kakao.json"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"


def load_config() -> dict[str, Any]:
    if not KAKAO_CONFIG.exists():
        raise FileNotFoundError(
            f"{KAKAO_CONFIG} 없음. config/kakao.example.json 을 복사해 kakao.json 을 만드세요."
        )
    with KAKAO_CONFIG.open(encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict[str, Any]) -> None:
    with KAKAO_CONFIG.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _with_client_secret(config: dict[str, Any], data: dict[str, str]) -> dict[str, str]:
    secret = config.get("client_secret", "").strip()
    if secret:
        data["client_secret"] = secret
    return data


def refresh_access_token(config: dict[str, Any]) -> dict[str, Any]:
    if not config.get("refresh_token"):
        raise ValueError("refresh_token 이 없습니다. python scripts/kakao_auth.py 로 먼저 인증하세요.")

    data = _with_client_secret(
        config,
        {
            "grant_type": "refresh_token",
            "client_id": config["rest_api_key"],
            "refresh_token": config["refresh_token"],
        },
    )
    response = requests.post(TOKEN_URL, data=data, timeout=30)
    result = response.json()
    if response.status_code != 200:
        raise RuntimeError(f"토큰 갱신 실패: {result}")

    if "access_token" in result:
        config["access_token"] = result["access_token"]
    if "refresh_token" in result:
        config["refresh_token"] = result["refresh_token"]

    save_config(config)
    return config


def get_valid_access_token() -> str:
    config = load_config()
    token = config.get("access_token")
    if not token:
        config = refresh_access_token(config)
        return config["access_token"]

    info = requests.get(
        "https://kapi.kakao.com/v1/user/access_token_info",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if info.status_code == 200:
        return token

    config = refresh_access_token(config)
    return config["access_token"]
