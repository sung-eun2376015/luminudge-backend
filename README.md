# LumiNudge Backend

영상 자막과 AI-1의 Attention 분석 결과를 이용해 개입 여부를 결정하고, 필요한 경우 Gemini로 아동 발달 티어에 맞는 질문을 생성하는 FastAPI 백엔드입니다.

## 현재 구현 범위

```text
YouTube URL + mock 자막 선택
          ↓
시청 세션 생성
          ↓
AI-1 ClsPayload 연속 입력
          ↓
intensity 및 Nudge 쿨다운 확인
          ↓
none   → 개입 없음
soft   → 영상 유지 + 루미 표시
strong → timestamp 기준 자막 선택
         → Gemini 질문 생성
         → 영상 정지 + 질문 반환
```

현재 구현 및 검증된 항목:

- `pinkfong`, `pororo` mock 자막 기반 세션 생성
- `none`, `soft`, `strong` Nudge 분기
- 세션별 개발용 10초 쿨다운
- timestamp 기준 현재/이전 자막 맥락 선택
- 실제 Gemini Tier별 질문 생성
- 프론트 전달용 `NudgeResponse`
- FastAPI 세션 및 Nudge API

아직 연결되지 않은 항목:

- 임의 YouTube URL의 실제 자막 추출
- AI-1의 실시간 `ClsPayload` 전송
- 프론트의 루미 표시, 영상 정지 및 질문 UI
- Redis/DB 기반 영구 세션 저장
- 실제 응답 평가와 ARI/PLR/CSR 리포팅

## 설치 및 실행

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

- 서버: `http://127.0.0.1:8000`
- Swagger API 문서: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health`

실제 Gemini 호출을 위해 프로젝트 루트의 `.env`에 API 키가 필요합니다.

```env
GEMINI_API_KEY=your_api_key
```

## API 사용법

### 1. 시청 세션 생성

```http
POST /sessions
```

Swagger에서 `POST /sessions` → `Try it out`을 누르고 실행합니다.

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=example",
  "subtitle_name": "pinkfong",
  "child_tier": "tier2"
}
```

- `youtube_url`: 사용자가 입력한 YouTube URL
- `subtitle_name`: MVP mock 자막 선택값 (`pinkfong` 또는 `pororo`)
- `child_tier`: 미션 난이도 (`tier1`, `tier2`, `tier3`)

응답:

```json
{
  "session_id": "생성된 세션 ID",
  "youtube_url": "https://www.youtube.com/watch?v=example",
  "subtitle_name": "pinkfong",
  "child_tier": "tier2",
  "caption_count": 21,
  "subtitle_source": "mock_data/subtitle_pinkfong.json"
}
```

현재 `youtube_url`은 세션에 저장만 하며 실제 자막 추출에는 사용하지 않습니다. `subtitle_name`은 mock 파일을 선택하기 위한 임시 필드이며, 실제 자막 연동 후 제거할 예정입니다.

### 2. Attention 결과 전송

세션 생성 응답의 `session_id`를 사용합니다.

```http
POST /sessions/{session_id}/nudge
```

요청은 `ai/attention/schemas.py`의 `ClsPayload` 형식을 따릅니다.

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

- `cls_score`: AI-1이 계산한 Cognitive Load Score (`0.0`~`1.0`)
- `intensity`: AI-1의 최종 개입 강도 (`none`, `soft`, `strong`)
- `gv`: Gaze Variance
- `fd`: Fixation Duration
- `br`: Blink Rate
- `timestamp`: 현재 YouTube 재생 시간(초)

AI-2는 `cls_score`로 강도를 다시 계산하지 않고 AI-1의 `intensity`에 따라 동작합니다. 쿨다운은 백엔드가 실제 경과 시간으로 관리하고, `timestamp`는 자막 선택에 사용합니다.

### 3. 미션 답변 전송

strong Nudge 응답의 `question.mission_id`를 사용합니다.

```http
POST /sessions/{session_id}/missions/{mission_id}/responses
```

선택형 답변:

```json
{
  "response_type": "choice",
  "answer": "파란색",
  "response_time_ms": 2800
}
```

음성 답변:

```json
{
  "response_type": "voice",
  "transcript": "방이 파란색으로 변했어요",
  "stt_source": "web_speech",
  "confidence": 0.91,
  "response_time_ms": 3400
}
```

응답:

```json
{
  "mission_id": "미션 ID",
  "response_type": "voice",
  "is_correct": true,
  "csr_score": 1.0,
  "plr_seconds": 3.4,
  "reaction": "praise",
  "feedback_text": "영상 내용을 정말 잘 기억했어!",
  "resume_video": true,
  "needs_retry": false,
  "needs_stt_fallback": false
}
```

- `praise`: 답변 성공, 영상 재개
- `hint`: 맥락 또는 정답이 부족하여 힌트 후 재시도
- `retry`: 음성 인식 실패 또는 제스처 미완료로 재시도
- 음성 답변은 `gemini-embedding-001` Sentence Embedding의 cosine similarity로 CSR을 계산합니다.
- 임베딩 API가 실패하면 기존 키워드 포함 비율 방식으로 자동 fallback합니다.
- 응답의 `csr_method`는 `semantic_embedding` 또는 `keyword_fallback`입니다.
- transcript가 비었거나 confidence가 `0.6` 미만이면 `needs_stt_fallback: true`를 반환합니다.

Web Speech fallback 오디오:

```http
POST /sessions/{session_id}/missions/{mission_id}/responses/audio
Content-Type: multipart/form-data
```

multipart 필드:

```text
audio              webm, wav, mp3, m4a 등 오디오 파일
response_time_ms   답변 시간(ms)
language           ko (기본값)
```

백엔드는 `gemini-2.5-flash`에 오디오 전사를 요청한 뒤 동일한 Semantic CSR 평가를 수행합니다. 앱 자체 업로드 제한은 10MB입니다. `hint`와 `retry`는 미션을 종료하지 않으며, `praise`가 반환될 때만 완료됩니다.

## 프론트 응답 계약

응답 형식은 `ai/nudge/schemas.py`의 `NudgeResponse`입니다.

### none: 개입 없음

```json
{
  "should_nudge": false,
  "intensity": "none",
  "cls_score": 0.3,
  "child_tier": "tier2",
  "timestamp": 5,
  "pause_video": false,
  "source": "no_trigger",
  "question": null,
  "attention": {
    "gv": 0.5,
    "fd": 1.2,
    "br": 10
  }
}
```

### soft: 루미만 표시

```json
{
  "should_nudge": true,
  "intensity": "soft",
  "cls_score": 0.6,
  "child_tier": "tier2",
  "timestamp": 22,
  "pause_video": false,
  "source": "soft_lumi",
  "question": null,
  "attention": {
    "gv": 0.2,
    "fd": 3.0,
    "br": 5
  }
}
```

### strong: 영상 정지 및 질문 표시

```json
{
  "should_nudge": true,
  "intensity": "strong",
  "cls_score": 0.8,
  "child_tier": "tier2",
  "timestamp": 35,
  "pause_video": true,
  "source": "mission_queue",
  "question": {
    "type": "choice",
    "text": "방이 무슨 색으로 변했을까요?",
    "choices": ["파란색", "노란색"]
  },
  "context_source": "current",
  "scene_summary": "노란 버튼을 누르자 방이 차가운 파란색으로 변하는 장면",
  "attention": {
    "gv": 0.1,
    "fd": 5.0,
    "br": 2
  }
}
```

프론트 처리 기준:

- `should_nudge`: Nudge UI 표시 여부
- `pause_video`: YouTube 영상 정지 여부
- `question.type`: `gesture`, `choice`, `open_question` 등 UI 유형
- `question.text`: 표시할 질문
- `question.choices`: 선택형 질문의 보기
- `source`: `no_trigger`, `cooldown`, `soft_lumi`, `mission_queue`, `fallback`

Gemini가 생성한 정답과 평가 기준은 프론트 응답에 노출하지 않습니다.

## 쿨다운

- 첫 Nudge는 즉시 실행합니다.
- Nudge 실행 후 같은 세션의 다음 개입을 10초 동안 보류합니다.
- `none`은 쿨다운을 시작하지 않습니다.
- 현재 10초는 개발·테스트 값이며 운영 목표값은 추후 확정합니다.
- 세션마다 별도의 `NudgeService`를 사용하므로 쿨다운도 독립적입니다.

서버를 재시작하면 현재 메모리 세션과 쿨다운 상태는 사라집니다.

## 테스트

자동 통합 테스트:

```powershell
python -m tests.ai.nudge.test_pinkfong_attention_flow
```

검증 항목:

1. `subtitle_pinkfong.json` 로드
2. 연속 `none → soft → strong` 입력
3. soft 이후 10초 쿨다운
4. timestamp 35초 자막 맥락 선택
5. Tier 2 선택형 질문 생성
6. `NudgeResponse` 출력 형식 검증

자동 테스트는 비용과 응답 변동을 피하기 위해 Gemini만 가짜 함수로 대체합니다. 실제 Gemini는 Swagger의 `POST /sessions/{session_id}/nudge` strong 요청으로 검증했으며, 자막에 맞는 선택형 질문이 정상적으로 반환됩니다.

성공 메시지:

```text
PASS: pinkfong subtitles + continuous CLS + cooldown + question output
```

## 주요 파일

```text
main.py                                       FastAPI 앱 설정 및 router 등록
mock_data/subtitle_pinkfong.json              핑크퐁 mock 자막
mock_data/subtitle_pororo.json                뽀로로 mock 자막
ai/attention/schemas.py                       AI-1 입력 스키마
ai/nudge/router.py                            세션·Nudge·답변 HTTP API
ai/nudge/caption_slicer.py                    timestamp 기반 자막 선택
ai/nudge/mission_generator.py                 Gemini 질문 생성
ai/nudge/audio_transcription_service.py       Gemini 오디오 전사
ai/nudge/nudge_trigger.py                     intensity별 응답 생성
ai/nudge/nudge_service.py                     쿨다운·자막·질문 통합
ai/nudge/response_service.py                  선택·음성·제스처 답변 평가
ai/nudge/schemas.py                           API 요청 및 프론트 출력 스키마
storage/memory.py                             MVP용 세션·미션 메모리 저장소
tests/ai/nudge/test_pinkfong_attention_flow.py 자동 통합 테스트
tests/ai/nudge/test_mission_response_flow.py   미션 저장·답변 API 통합 테스트
tests/ai/nudge/test_audio_transcription_service.py Gemini 오디오 전사 테스트
```

## 다음 연결 단계

1. Dev가 실제 YouTube 자막을 확보하는 방식 확정
2. mock `subtitle_name`을 실제 captions 입력 또는 자막 추출기로 교체
3. AI-1이 세션 ID와 함께 `ClsPayload`를 실시간 전송
4. 프론트가 `NudgeResponse`에 따라 루미, 영상 및 질문 UI 제어
5. Redis/DB 세션 저장과 운영용 쿨다운 설정
