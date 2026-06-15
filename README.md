# AI Daily Coach

비전공 실무자용 **AI 학습 코치** — 매일 **07:30 KST** Telegram 자동 발송.  
**Gemini**가 RSS 뉴스 + 3개월 커리큘럼 기반으로 **매일 새 브리핑** 생성.  
PC·Cursor 불필요 — **GitHub Actions**.

---

## 아키텍처 (MVP)

```
07:30 GitHub Actions
  → RSS 뉴스 수집 (fetch_ai_news.py)
  → 커리큘럼 다음 개념 (curriculum_manager.py)
  → Gemini 생성 (generate_daily_briefing.py)
  → Telegram 전송
  → state.json commit (진도 저장)
```

| 파일 | 역할 |
|------|------|
| `data/curriculum.json` | 3개월·36개 개념 로드맵 |
| `data/state.json` | 진도·중복 방지 |
| `prompts/daily_coach.md` | Gemini 프롬프트 |
| `.github/workflows/daily-briefing.yml` | 스케줄 |

---

## 1. Gemini API 키 (1회)

1. [Google AI Studio](https://aistudio.google.com/apikey) → **Create API key**
2. 로컬:

```powershell
cd "C:\Users\pyww2\Desktop\cursor\AI개념"
Copy-Item config\gemini.example.json config\gemini.json
# notepad config\gemini.json → api_key 붙여넣기
```

3. GitHub Secrets: **`GEMINI_API_KEY`** (필수)

---

## 2. Telegram (1회)

```powershell
Copy-Item config\telegram.example.json config\telegram.json
# bot_token 저장 후
python scripts/get_telegram_chat_id.py
python scripts/send_telegram.py --text "연결 테스트"
```

GitHub Secrets: `BRIEFING_CHANNEL=telegram`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

---

## 3. GitHub Secrets

```powershell
python scripts/print_github_secrets.py
```

| Secret | 값 |
|--------|-----|
| `BRIEFING_CHANNEL` | `telegram` |
| `GEMINI_API_KEY` | Google AI Studio |
| `TELEGRAM_BOT_TOKEN` | telegram.json |
| `TELEGRAM_CHAT_ID` | telegram.json |
| `GEMINI_MODEL` | (선택) `gemini-2.0-flash` |

**Settings → Actions → Workflow permissions → Read and write**

---

## 4. 테스트

```powershell
# 로컬 전체 파이프라인 (Gemini + Telegram)
python scripts/run_scheduled_briefing.py
```

GitHub: **Actions → Daily AI Briefing → Run workflow**

---

## 브리핑 구성 (매일 1통)

1. **오늘의 AI 뉴스** (RSS 2건)
2. **오늘의 AI 개념** (커리큘럼)
3. **AX 실무** (재무·SAP·결산 관점)
4. **Agent 아이디어** (1개)

---

## 비용

- GitHub Actions + Telegram: **0원**
- Gemini: **무료 한도** (1일 1회 기준 일반적으로 가능)

---

## 레거시

- `content/library/` — 이전 고정 원고 (MVP 이후 미사용)
- `data/topics.json` — 이전 순환 방식
