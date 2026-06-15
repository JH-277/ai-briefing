"""카카오 로그인 페이지를 브라우저에서 엽니다."""
import json
import webbrowser
from pathlib import Path

c = json.loads(Path(__file__).resolve().parent.parent.joinpath("config/kakao.json").read_text(encoding="utf-8"))
url = (
    "https://kauth.kakao.com/oauth/authorize"
    f"?response_type=code&client_id={c['rest_api_key']}"
    f"&redirect_uri={c['redirect_uri']}&scope=talk_message&prompt=consent"
)
webbrowser.open(url)
print("브라우저에서 카카오 로그인 페이지를 열었습니다.")
