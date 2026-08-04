# LumiNudge Backend

프론트엔드 AI-1의 Attention 분석 결과를 받아 아동 맞춤형 Nudge를 생성하는
FastAPI 백엔드입니다. 프론트는 카메라 영상을 서버로 보내지 않고 브라우저에서
계산한 `ClsPayload`만 전송합니다.

## API 문서

서버 실행 후 다음 문서를 사용할 수 있습니다.

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Health Check: `http://127.0.0.1:8000/health`

## 실행

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

프로젝트 루트에 `.env`를 생성합니다.

```env
GEMINI_API_KEY=your_api_key
DATABASE_URL=postgresql://...
SESSION_STORAGE=database
```

- `SESSION_STORAGE=database`: 운영 기본값. 세션, Attention 이벤트, 미션을 DB에 저장합니다.
- `SESSION_STORAGE=memory`: 외부 DB 없이 실행하는 테스트 전용 모드입니다.

DB에는 `migrations/001_onboarding_child_tier.sql`,
`migrations/002_session_mission_storage.sql`,
`migrations/003_onboarding_plr_nullable.sql`을 순서대로 적용합니다. 앱 시작 시
SQLModel의 `create_all`도 실행되지만 기존 테이블 변경은 migration을 기준으로 관리합니다.

## 전체 프론트 연동 흐름

```text
1. POST /onboarding
   → onboarding_id 보관

2. POST /sessions
   → session_id 보관

3. 프론트에서 카메라/센서와 AI-1 실행
   → POST /sessions/{session_id}/nudge

4. NudgeResponse 처리
   → none: 아무 동작 없음
   → soft: Lumi 표시
   → strong: 영상 정지 + 질문 표시 + mission_id 보관

5. POST /sessions/{session_id}/missions/{mission_id}/responses
   → praise: 성공 표시 후 영상 재생
   → hint/retry: 영상 정지 유지 후 재응답

6. Web Speech 실패 시
   → POST .../responses/audio
   → Gemini 음성 전사 및 CSR 평가
```

## 프론트 ID 보관 규칙

| ID | 권장 보관 위치 | 수명 |
|---|---|---|
| `onboarding_id` | 사용자 상태 또는 `localStorage` | 아동 프로필 유지 기간 |
| `session_id` | 전역 상태 + `sessionStorage` | 한 영상의 시청 세션 |
| `mission_id` | 현재 질문 컴포넌트 상태 | 질문 완료까지 |

세션이 `404`를 반환하면 프론트는 기존 `session_id`를 버리고 새 세션을 생성합니다.

## 시간 단위

| 필드 | 단위 | 기준 |
|---|---:|---|
| `timestamp` | 초 | 영상 시작점부터 현재 재생 위치 |
| `video_duration_sec` | 초 | 영상 전체 길이 |
| `response_time_ms` | 밀리초 | 질문 표시부터 응답 완료까지 |
| `cooldown_ms` | 밀리초 | 프론트에서 적용한 Nudge 제한 시간 |
| `plr_seconds` | 초 | 백엔드가 응답 시간으로 계산한 값 |

`timestamp`에는 Unix timestamp가 아니라 YouTube Player의 `getCurrentTime()` 값을 사용합니다.

## 1. 온보딩 생성

```http
POST /onboarding
Content-Type: application/json
```

```json
{
  "ageYears": 4,
  "gender": "female",
  "canFollowSimpleInstruction": true,
  "canSpeak": true,
  "baselineGV": 0.25,
  "baselineFD": 1.2,
  "baselineBR": 15,
  "plr": null,
  "completedAt": "2026-08-01T12:00:00+09:00"
}
```

`plr`은 프론트에서 아직 측정하지 못한 경우 `null`로 전달할 수 있습니다.

```json
{
  "onboarding_id": 17,
  "child_tier": "tier2"
}
```

## 2. 시청 세션 생성

### 실제 자막 전달

`captions`가 있으면 백엔드는 해당 자막을 우선 사용합니다.

```http
POST /sessions
Content-Type: application/json
```

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=example",
  "onboarding_id": 17,
  "captions": [
    {"start": 28, "duration": 15, "text": "방의 온도가 파란색으로 변해요."},
    {"start": 43, "duration": 15, "text": "친구들이 버튼을 다시 눌러요."}
  ]
}
```

프론트는 `start`, `duration`, `text`를 보내는 것을 권장합니다. 이미 종료 시점을
제공하는 자막 모듈과의 호환을 위해 `duration` 대신 `end`를 보내는 것도 허용합니다.

### 개발용 mock 자막

실제 자막 연결 전에는 `subtitle_name`으로 `pinkfong` 또는 `pororo`를 사용합니다.

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=example",
  "onboarding_id": 17,
  "subtitle_name": "pinkfong"
}
```

`captions`와 `subtitle_name` 중 하나는 반드시 필요합니다.

응답:

```json
{
  "session_id": "session-id",
  "onboarding_id": 17,
  "youtube_url": "https://www.youtube.com/watch?v=example",
  "subtitle_name": null,
  "child_tier": "tier2",
  "caption_count": 2,
  "subtitle_source": "provided_captions"
}
```

## 3. Attention 결과와 Nudge

AI-1은 프론트에서 실행하며 프론트가 결과를 백엔드에 전달합니다.

```http
POST /sessions/{session_id}/nudge
Content-Type: application/json
```

```json
{
  "cls_score": 0.8,
  "intensity": "strong",
  "gv": 0.1,
  "fd": 5.0,
  "br": 2,
  "timestamp": 35.2,
  "video_duration_sec": 300,
  "cooldown_ms": 10000
}
```

백엔드는 `intensity`를 다시 계산하지 않고 AI-1이 결정한 값을 사용합니다.
`cooldown_ms` 역시 기록용이며 실제 cooldown 제어는 프론트가 담당합니다.

### 프론트 처리 규칙

| 응답 | `pause_video` | 프론트 처리 |
|---|---:|---|
| `none` | `false` | 아무 Nudge도 표시하지 않음 |
| `soft` | `false` | Lumi 안내 UI 표시 |
| `strong` | `true` | 영상 정지 후 `question` 표시 |

strong 응답 예시:

```json
{
  "should_nudge": true,
  "intensity": "strong",
  "cls_score": 0.8,
  "child_tier": "tier2",
  "timestamp": 35.2,
  "pause_video": true,
  "source": "mission_queue",
  "question": {
    "mission_id": "mission-id",
    "type": "choice",
    "text": "방의 온도를 바꾼 것은 무엇일까요?",
    "choices": ["노란색 버튼", "파란색 공"]
  },
  "context_source": "current",
  "scene_summary": "방의 온도가 바뀌는 장면",
  "attention": {"gv": 0.1, "fd": 5.0, "br": 2}
}
```

## 4. 미션 응답

```http
POST /sessions/{session_id}/missions/{mission_id}/responses
Content-Type: application/json
```

선택형:

```json
{
  "response_type": "choice",
  "answer": "노란색 버튼",
  "response_time_ms": 2800
}
```

Web Speech 음성 응답:

```json
{
  "response_type": "voice",
  "transcript": "방이 파란색으로 변했어요",
  "stt_source": "web_speech",
  "confidence": 0.91,
  "response_time_ms": 3400
}
```

제스처:

```json
{
  "response_type": "gesture",
  "completed": true,
  "response_time_ms": 1800
}
```

응답의 `reaction`은 `praise`, `hint`, `retry` 중 하나입니다. 프론트는
`resume_video`가 `true`일 때만 영상을 다시 재생합니다.

## 5. 음성 fallback

```http
POST /sessions/{session_id}/missions/{mission_id}/responses/audio
Content-Type: multipart/form-data
```

| 필드 | 설명 |
|---|---|
| `audio` | webm, wav, mp3, m4a 등, 최대 10MB |
| `response_time_ms` | 질문 표시 후 응답까지 밀리초 |
| `language` | 기본값 `ko` |

일반 응답 API에서 `needs_stt_fallback: true`가 반환될 때 사용합니다.

## 오류 코드

| 코드 | 의미 | 프론트 처리 |
|---:|---|---|
| `400` | 잘못된 음성 파일 | 다시 녹음 안내 |
| `404` | 온보딩, 세션 또는 미션 없음 | 세션 재생성 또는 화면 종료 |
| `409` | 이미 완료된 미션 | 중복 제출 중단 |
| `422` | 요청 필드 또는 형식 오류 | 요청 생성 코드 확인 |
| `502` | Gemini 질문 생성 또는 전사 실패 | 재시도 UI 또는 일반 Nudge fallback |

## 저장 구조

- `onboarding_records`: 아동 온보딩과 tier
- `viewing_sessions`: 영상 세션, 자막, baseline
- `attention_events`: AI-1 입력 및 Nudge 처리 결과
- `missions`: 생성 질문, 정답, 응답 이력 및 상태

프로세스 캐시는 반복 조회 최적화용이며 DB가 원본입니다. 서버가 재시작되어도 DB에서
세션과 미션을 복원할 수 있습니다.

## 테스트

```powershell
python -m tests.ai.nudge.test_pinkfong_attention_flow
python -m tests.ai.nudge.test_mission_response_flow
python -m tests.ai.nudge.test_audio_transcription_service
python -m tests.ai.nudge.test_semantic_csr
python -m tests.ai.nudge.test_database_storage
```

테스트는 `SESSION_STORAGE=memory`를 사용하고 Gemini 호출은 mock으로 대체합니다.
