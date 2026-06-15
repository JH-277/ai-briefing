# AI 개념 자동 브리핑 — Loop Agent 지시문

Cursor `/loop` 틱이 발생할 때 이 파일을 따르세요. **한 턴 안에** 아래 1~6을 모두 수행합니다.

## 역할

비전공자에게 AI 개념을 **3~5분 분량**으로 쉽게 브리핑하고, 결과를 카카오톡으로 보냅니다.

## 실행 순서

### 1. 다음 주제 가져오기

```powershell
python scripts/topic_manager.py next
```

출력 JSON의 `id`, `title`, `prompt_hint` 를 사용합니다.

### 2. 브리핑 작성 (웹 검색 권장)

`prompt_hint` 를 바탕으로 최신·정확한 내용을 조사한 뒤, 아래 **고정 형식**으로 `briefings/{id}-{YYYY-MM-DD}.md` 에 저장합니다.

```markdown
# 📌 {title}

## 한 줄 정의
(1문장)

## 왜 중요한가
(일상·업무 관점 2~3문장)

## 핵심 설명
(비유 1개 + 핵심 포인트 3~5개, 불릿)

## 헷갈리기 쉬운 점
(1가지)

## 오늘의 키워드
- 키워드1, 키워드2, 키워드3

---
💬 추가 질문은 Cursor 채팅에서 이어가세요.
```

**작성 원칙**
- 전문 용어는 처음 등장 시 괄호로 풀어쓰기
- 코드·수식 최소화
- 본문 800~1500자 (카카오 전송용 요약은 별도)

### 3. 카카오용 짧은 요약 만들기

같은 파일 하단에 `## 카카오 요약` 섹션을 추가하거나, 별도로 아래 구조의 **600자 이내** 텍스트를 준비:

```
📌 {title}

한 줄: ...
왜: ...
핵심: • ... • ... • ...
헷갈림: ...
```

### 4. 카카오톡 전송

```powershell
python scripts/send_kakao.py --file briefings/{파일명}.md --title "{title}"
```

실패 시:
- `config/kakao.json` 없음 → README 카카오 설정 참고
- 401 → `python scripts/kakao_auth.py` 재인증 안내를 사용자에게 짧게 남기고 종료

### 5. 상태 갱신

```powershell
python scripts/topic_manager.py complete {topic_id}
```

### 6. 턴 마무리

사용자에게 한 줄로 보고:
- 오늘 주제, 파일 경로, 카카오 전송 성공 여부, 다음 주제 예고

## 주제 추가·수정

`data/topics.json` 의 `topics` 배열에 객체 추가:

```json
{
  "id": "고유-id",
  "title": "표시 제목",
  "prompt_hint": "에이전트가 조사할 방향"
}
```

## 주의

- Phase 3(카카오 챗봇 Q&A)은 **구현하지 않음**
- 추가 질문은 Cursor 채팅에서 처리
- `config/kakao.json` 은 git에 올리지 않음
