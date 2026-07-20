# LumiNudge Backend

FastAPI 기반 LumiNudge 백엔드입니다. 현재 Nudge 파트는 영상 자막과 AI-1의 Attention 결과를 받아 개입 여부와 프론트 표시용 질문을 생성합니다.

## 현재 Nudge 흐름

```text
mock_data/subtitle_pinkfong.json 한 번 로드
                +
AI-1에서 ClsPayload 연속 입력
                ↓
intensity와 10초 쿨다운 확인
                ↓
none   → 개입 없음
soft   → 영상 유지 + 루미만 표시
strong → timestamp 기준 자막 선택
         → Gemini로 티어별 질문 생성
         → 영상 일시정지 + 질문을 프론트에 반환
```

`timestamp`는 YouTube 영상 재생 시간(초)이며 자막 선택에 사용합니다. 쿨다운은 영상 시간이 아니라 서버의 실제 경과 시간으로 계산합니다. 첫 Nudge는 기다리지 않고 실행하며, 실행 후 10초 동안 다음 Nudge를 보류합니다. 운영용 쿨다운은 추후 조정합니다.

## AI-1 입력 형식

`ai/attention/schemas.py`의 `ClsPayload`를 사용합니다.

```json
{
  "cls_score": 0.8,
  "intensity": "strong",
  "gv": 0.1,
  "fd": 4.5,
  "br": 3,
  "timestamp": 35
}
```

- `cls_score`: AI-1이 계산한 Cognitive Load Score (`0.0`~`1.0`)
- `intensity`: AI-1의 최종 개입 강도 (`none`, `soft`, `strong`)
- `gv`, `fd`, `br`: 판단 근거가 된 Attention 지표
- `timestamp`: 현재 YouTube 재생 시간(초)

AI-2는 `cls_score`로 강도를 다시 계산하지 않고 AI-1이 전달한 `intensity`에 따라 동작합니다. `cls_score`와 Attention 지표는 기록과 리포팅에 사용합니다.

## 프론트 출력 형식

출력 계약은 `ai/nudge/schemas.py`의 `NudgeResponse`입니다.

### 개입 없음

```json
{
  "should_nudge": false,
  "intensity": "none",
  "cls_score": 0.3,
  "child_tier": "tier2",
  "timestamp": 5.0,
  "pause_video": false,
  "source": "no_trigger",
  "attention": {
    "gv": 0.1,
    "fd": 4.5,
    "br": 3
  }
}
```

### 약한 개입

`soft`는 질문 없이 루미만 표시합니다.

```json
{
  "should_nudge": true,
  "intensity": "soft",
  "cls_score": 0.6,
  "child_tier": "tier2",
  "timestamp": 22.0,
  "pause_video": false,
  "source": "soft_lumi",
  "attention": {
    "gv": 0.1,
    "fd": 4.5,
    "br": 3
  }
}
```

### 강한 개입과 질문

```json
{
  "should_nudge": true,
  "intensity": "strong",
  "cls_score": 0.8,
  "child_tier": "tier2",
  "timestamp": 35.0,
  "pause_video": true,
  "source": "mission_queue",
  "question": {
    "type": "choice",
    "text": "방금 방의 온도를 바꾼 것은 무엇일까요?",
    "choices": ["노란색 버튼", "파란색 공"]
  },
  "context_source": "current",
  "scene_summary": "노란색 버튼을 누르자 방의 온도가 변하는 장면",
  "attention": {
    "gv": 0.1,
    "fd": 4.5,
    "br": 3
  }
}
```

프론트 처리 기준:

- `should_nudge`: Nudge UI 표시 여부
- `pause_video`: YouTube 영상 일시정지 여부
- `question.type`: `gesture`, `choice`, `open_question` 등 미션 UI 종류
- `question.text`: 화면에 표시할 질문
- `question.choices`: 선택형 질문의 보기
- `source`: `no_trigger`, `cooldown`, `soft_lumi`, `mission_queue`, `fallback`

Gemini가 생성한 정답이나 평가 기준은 프론트 응답에 노출하지 않습니다.

## 최종 Nudge 통합 테스트

현재 유지하는 Nudge 테스트는 다음 하나입니다.

```text
tests/ai/nudge/test_pinkfong_attention_flow.py
```

실행:

```powershell
python -m tests.ai.nudge.test_pinkfong_attention_flow
```

검증 내용:

1. `subtitle_pinkfong.json`을 실제로 로드
2. `none → soft → strong` 형태의 연속 `ClsPayload` 입력
3. soft에서 루미만 표시
4. soft 이후 10초 이내 strong 요청을 쿨다운으로 차단
5. 10초 경과 후 timestamp 35초의 핑크퐁 자막 선택
6. Tier 2 선택형 질문 생성
7. `NudgeResponse` 형식 검증 및 프론트 전달 JSON 출력

테스트는 API 비용 없이 전체 흐름을 확인하기 위해 Gemini 응답만 가짜 함수로 대체합니다. 실제 실행에서는 같은 자막 맥락이 `mission_generator.py`의 Gemini 호출로 전달됩니다.

성공 출력:

```text
PASS: pinkfong subtitles + continuous CLS + cooldown + question output
```

## 주요 파일

```text
main.py                                      FastAPI 애플리케이션
mock_data/subtitle_pinkfong.json             테스트 영상 자막
ai/attention/schemas.py                      AI-1 입력 스키마
ai/nudge/caption_slicer.py                   timestamp 기준 자막 선택
ai/nudge/mission_generator.py                Gemini 질문 생성
ai/nudge/nudge_trigger.py                    intensity별 응답 생성
ai/nudge/nudge_service.py                    Attention·쿨다운·자막·질문 통합
ai/nudge/schemas.py                          프론트 출력 스키마
tests/ai/nudge/test_pinkfong_attention_flow.py 최종 통합 테스트
```

## 설치 및 서버 실행

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

- 서버: `http://127.0.0.1:8000`
- API 문서: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health`

## MVP 세션 API 사용법

현재는 사용자가 입력한 YouTube URL을 세션에 저장하고, `subtitle_name`으로 `pinkfong` 또는 `pororo` 예시 자막을 선택합니다.

1. 서버 실행 후 `http://127.0.0.1:8000/docs`에 접속합니다.
2. `POST /sessions`에서 `Try it out`을 누르고 다음 요청을 실행합니다.

```json
{
  "youtube_url": "핑크퐁 YouTube URL",
  "subtitle_name": "pinkfong",
  "child_tier": "tier2"
}
```

3. 응답의 `session_id`를 복사합니다.
4. `POST /sessions/{session_id}/nudge`의 `session_id` 칸에 붙여 넣고 `ClsPayload`를 전송합니다.

```json
{
  "cls_score": 0.8,
  "intensity": "strong",
  "gv": 0.1,
  "fd": 5.0,
  "br": 2,
  "timestamp": 35
}
```

`subtitle_name`은 현재 `pinkfong`과 `pororo`만 허용합니다. `none`과 `soft`는 Gemini를 호출하지 않습니다. `strong`은 `.env`의 `GEMINI_API_KEY`를 사용해 실제 질문을 생성합니다. 각 세션은 독립된 10초 Nudge 쿨다운을 가집니다. 서버를 재시작하면 MVP 메모리 세션은 사라집니다.

현재 `NudgeService`, 출력 계약, FastAPI 세션/Nudge 엔드포인트까지 구현되어 있습니다. 실제 YouTube 자막 추출과 AI-1·프론트 실시간 연결은 다음 단계입니다.
