# AI 개념 자동 브리핑

비전공자용 AI 숏츠 브리핑을 **매일 07:30** 자동 전송.  
**PC·Cursor 불필요** — GitHub Actions + **100% 무료**.

**전송 채널:** **Telegram 권장** (완전 자동화) · Kakao 선택 가능

---

## Kakao vs Telegram (추천)

| | **Telegram** ⭐ 권장 | **Kakao** |
|---|---------------------|-----------|
| **완전 자동화** | ✅ 봇 토큰 **만료 거의 없음** | ⚠️ 2~3개월마다 **토큰 재발급** → GitHub Secrets 수정 |
| **GitHub 연동** | ✅ API 1줄, 설정 **5분** | ✅ 가능 (이미 구현) |
| **한국 일상 편의** | 보통 씀 | **매일 쓰는 앱** |
| **보안** | Secrets 유출 시 **내 봇 채팅**으로만 전송 가능 | Secrets 유출 시 **내 카톡**으로 전송 |
| **추가 Q&A (나중에)** | ✅ 봇 **양방향** 쉬움 | ❌ 나에게 보내기만 (일방향) |
| **비용** | 무료 | 무료 쿼터 |

**결론:** GitHub **무인 7:30** → **Telegram**. 카톡이 익숙하면 `both` 가능.

---

## A. Telegram 설정 (5분, 1회)

### 1) 봇 만들기

1. 텔레그램에서 **@BotFather** 검색  
2. `/newbot` → 이름·username 입력  
3. **bot token** 복사 (예: `7123456789:AAH...`)

### 2) chat_id 받기

```powershell
cd "C:\Users\pyww2\Desktop\cursor\AI개념"
Copy-Item config\telegram.example.json config\telegram.json
# notepad config\telegram.json  → bot_token 붙여넣기
python scripts/get_telegram_chat_id.py
```

봇에게 `/start` 보낸 뒤 스크립트 실행 → `chat_id` 자동 저장.

### 3) 테스트

```powershell
python scripts/send_telegram.py --text "연결 테스트"
```

---

## B. GitHub Actions (노트북 OFF)

### 1) GitHub에 코드 올리기

**방법 1 — Git 설치됨**

```powershell
cd "C:\Users\pyww2\Desktop\cursor\AI개념"
git init
git add .
git commit -m "AI briefing automation"
git remote add origin https://github.com/YOUR_ID/ai-briefing.git
git push -u origin main
```

**방법 2 — Git 없음**  
[github.com/new](https://github.com/new) → 저장소 생성 → **Add file → Upload files** → `AI개념` 폴더 전체 업로드  
(`config/kakao.json`, `config/telegram.json` 은 **올리지 마세요**)

### 2) Secrets 등록

```powershell
python scripts/print_github_secrets.py
```

GitHub → **Settings → Secrets → Actions**

| Secret | 값 |
|--------|-----|
| `BRIEFING_CHANNEL` | `telegram` (또는 `kakao` / `both`) |
| `TELEGRAM_BOT_TOKEN` | telegram.json |
| `TELEGRAM_CHAT_ID` | telegram.json |
| `KAKAO_*` | kakao 사용 시만 |

### 3) Actions 권한

**Settings → Actions → Workflow permissions** → **Read and write** → Save

### 4) 수동 테스트

**Actions → Daily AI Briefing → Run workflow**

성공 후 **매일 07:30 KST** 자동.

---

## C. Kakao만 쓸 때 (선택)

이미 설정했다면 Secrets에 `BRIEFING_CHANNEL` = `kakao` + Kakao Secrets.  
**2~3개월마다** `kakao_auth.py` 재로그인 → `KAKAO_REFRESH_TOKEN` Secrets 업데이트.

---

## 콘텐츠

- **10편** 숏츠형: `content/library/`
- **후보 주제:** `data/topic_backlog.json`
- **가이드:** `prompts/clip_format.md`

---

## 로컬 1회 테스트

```powershell
python scripts/run_scheduled_briefing.py
```

`config/settings.json` → `"delivery_channel": "telegram"`

---

## 비용

GitHub Actions + Telegram + (선택) Kakao = **0원** (일 1회 기준)
