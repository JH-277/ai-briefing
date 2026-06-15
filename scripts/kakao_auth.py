"""카카오 로그인 최초 인증 — 인가 코드로 토큰 발급."""

from __future__ import annotations

import json
import sys
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from kakao_token import KAKAO_CONFIG, save_config, _with_client_secret  # noqa: E402

AUTH_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"


def load_or_create_config() -> dict:
    example = ROOT / "config" / "kakao.example.json"
    if not KAKAO_CONFIG.exists():
        if not example.exists():
            raise FileNotFoundError("config/kakao.example.json 이 없습니다.")
        with example.open(encoding="utf-8") as f:
            config = json.load(f)
        with KAKAO_CONFIG.open("w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"생성됨: {KAKAO_CONFIG}")
        print("rest_api_key 를 카카오 개발자 콘솔 값으로 수정한 뒤 다시 실행하세요.")
        sys.exit(0)

    with KAKAO_CONFIG.open(encoding="utf-8") as f:
        return json.load(f)


def extract_code(raw: str) -> str:
    raw = raw.strip()
    if "code=" in raw:
        if raw.startswith("http"):
            return parse_qs(urlparse(raw).query)["code"][0]
        if "code=" in raw:
            return raw.split("code=")[1].split("&")[0]
    return raw


def main() -> None:
    config = load_or_create_config()
    rest_api_key = config.get("rest_api_key", "")
    redirect_uri = config.get("redirect_uri", "http://localhost:8080/oauth")

    if not rest_api_key or rest_api_key == "YOUR_KAKAO_REST_API_KEY":
        print("config/kakao.json 의 rest_api_key 를 설정하세요.")
        sys.exit(1)

    auth_link = (
        f"{AUTH_URL}?response_type=code"
        f"&client_id={rest_api_key}"
        f"&redirect_uri={redirect_uri}"
        f"&scope=talk_message"
        f"&prompt=consent"
    )
    print("\n=== 카카오 로그인 ===")
    print("1. 브라우저에서 로그인·동의")
    print("2. 동의 화면에서 「카카오톡 메시지 전송」을 꼭 체크(또는 동의)")
    print("3. 리다이렉트된 URL 전체를 복사해 아래에 붙여넣기\n")
    print(auth_link + "\n")
    webbrowser.open(auth_link)

    pasted = input("리다이렉트 URL 또는 code 값: ").strip()
    code = extract_code(pasted)

    data = _with_client_secret(
        config,
        {
            "grant_type": "authorization_code",
            "client_id": rest_api_key,
            "redirect_uri": redirect_uri,
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
    print("\n토큰 저장 완료. python scripts/send_kakao.py --text \"테스트\" 로 확인하세요.")


if __name__ == "__main__":
    main()
