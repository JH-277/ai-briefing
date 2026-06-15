# AI 개념 자동 브리핑 Agent

비전공자를 위한 AI 개념 브리핑을 주기적으로 생성하고 카카오톡으로 전송합니다.

## Loop 실행 시

`prompts/loop_briefing.md` 의 1~6단계를 **한 턴에** 수행하세요.

## 자동 스케줄 (매일 07:30)

```text
/loop daily scripts/start_daily_730.ps1 를 백그라운드로 실행하고, loop_briefing 지시문대로 매일 07:30에 브리핑+카카오 전송
```

또는 Cursor 채팅: `매일 7시 30분 브리핑 루프 시작해줘`

## 주요 명령

| 명령 | 설명 |
|------|------|
| `python scripts/topic_manager.py next` | 다음 주제 |
| `python scripts/send_kakao.py --file briefings/xxx.md --title "제목"` | 카카오 전송 |
| `python scripts/topic_manager.py complete {id}` | 완료 처리 |

## 카카오 설정

`config/kakao.json` 필요. 최초 1회 `python scripts/kakao_auth.py`

## Loop 프롬프트 (복사용)

```
/loop 24h prompts/loop_briefing.md 지시문대로 AI 개념 브리핑 1건 생성 후 카카오 전송까지 완료하세요.
```
