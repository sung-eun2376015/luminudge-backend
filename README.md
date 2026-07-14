# LumiNudge Backend

LumiNudge의 FastAPI 백엔드와 AI 기반 Nudge 생성 모듈을 관리하는 저장소입니다.

현재 백엔드는 영상별 자막 데이터를 제공하며, AI Nudge 모듈은 자막과 현재 영상 시간을 기반으로 영유아용 미션을 생성합니다.

## 현재 구현 상태

구현 완료:

- FastAPI 서버
- 영상별 mock 자막 조회
- 자막 타임스탬프 기반 현재/이전 맥락 선택
- Gemini 기반 티어별 미션 생성
- T-5초 미션 사전 생성
- 메모리 기반 Mission Queue
- CLS 점수 기반 Nudge 판단
- STT 결과 정규화
- 키워드 기반 CSR 응답 평가

아직 연결되지 않은 부분:

- 프론트엔드와 AI Nudge API 연결
- AI-1의 실제 CLS 결과 연결
- 실제 자막 추출 파이프라인
- 영구 저장소 기반 Mission Queue
- 실제 프론트엔드 STT 입력 연결

## 프로젝트 구조

```text
luminudge-backend/
├─ main.py
├─ requirements.txt
├─ .env
├─ mock_data/
│  ├─ subtitle_pinkfong.json
│  └─ subtitle_pororo.json
├─ ai/
│  ├─ __init__.py
│  └─ nudge/
│     ├─ __init__.py
│     ├─ caption_slicer.py
│     ├─ mission_generator.py
│     ├─ mission_prompt.txt
│     ├─ prefetch_queue.py
│     ├─ nudge_trigger.py
│     ├─ stt_adapter.py
│     ├─ stt_csr.py
│     └─ response_evaluator.py
└─ tests/
   ├─ ai/
   │  └─ nudge/
   └─ fixtures/
      └─ nudge/
```

## 개발 환경 설정

가상환경을 생성합니다.

```powershell
python -m venv .venv
```

Windows PowerShell에서 가상환경을 활성화합니다.

```powershell
.\.venv\Scripts\Activate.ps1
```

의존성을 설치합니다.

```powershell
python -m pip install -r requirements.txt
```

백엔드 루트에 `.env` 파일을 만들고 Gemini API 키를 설정합니다.

```env
GEMINI_API_KEY=your_api_key
```

`.env`는 Git에 포함하지 않습니다.

## 서버 실행

```powershell
uvicorn main:app --reload
```

기본 주소:

```text
http://localhost:8000
```

API 문서:

```text
http://localhost:8000/docs
```

Health Check:

```http
GET /health
```

## Mock 자막 데이터

현재 데모에서는 자막을 다음 위치에 저장합니다.

```text
mock_data/subtitle_{video_name}.json
```

예:

```text
mock_data/subtitle_pinkfong.json
mock_data/subtitle_pororo.json
```

파일명과 API 경로는 다음과 같이 연결됩니다.

```http
GET /subtitles/pinkfong
GET /subtitles/pororo
```

새 영상을 추가할 때는 다음처럼 파일을 생성합니다.

```text
mock_data/subtitle_new_video.json
```

호출 경로:

```http
GET /subtitles/new_video
```

## 자막 입력 계약

AI Nudge 모듈에 전달하는 자막은 JSON 배열이어야 합니다.

```json
[
  {
    "start": 0,
    "end": 15,
    "text": "해당 시간대의 장면 설명 또는 자막"
  },
  {
    "start": 15,
    "end": 28,
    "text": "다음 시간대의 장면 설명 또는 자막"
  }
]
```

필드:

- `start`: 자막 시작 시간, 초 단위
- `end`: 자막 종료 시간, 초 단위
- `text`: 해당 구간의 자막 또는 장면 설명

현재 `mock_data`는 데모용 저장 방식입니다. AI Nudge 코드는 특정 파일명에 의존하지 않으며, 위 형식의 자막 배열이라면 API 요청이나 데이터베이스에서 전달받아도 처리할 수 있습니다.

## AI Nudge 처리 흐름

```text
자막 배열 + 현재 영상 시간
→ 현재 및 이전 자막 맥락 선택
→ 5초 뒤 사용할 미션 사전 생성
→ Gemini 티어별 미션 생성
→ Mission Queue 저장
→ CLS 조건 만족 시 Nudge Event 생성
```

주요 모듈:

- `caption_slicer.py`: 현재 시간 기준 자막 맥락 선택
- `mission_generator.py`: Gemini 기반 티어별 미션 생성
- `prefetch_queue.py`: 5초 뒤 미션 사전 생성 및 큐 관리
- `nudge_trigger.py`: CLS 기반 개입 판단
- `stt_adapter.py`: STT payload 표준화
- `stt_csr.py`: 키워드 기반 CSR 평가
- `response_evaluator.py`: STT부터 CSR까지 통합 평가

## Gemini 미션 출력

```json
{
  "should_generate": true,
  "context_source": "current",
  "scene_summary": "현재 영상 장면 요약",
  "keywords": ["핵심", "키워드"],
  "missions": {
    "tier1": {
      "type": "gesture",
      "prompt": "간단한 동작을 따라 해볼까?"
    },
    "tier2": {
      "type": "choice",
      "prompt": "화면에 나온 것은 무엇일까?",
      "choices": ["선택 1", "선택 2"],
      "answer": "선택 1"
    },
    "tier3": {
      "type": "open_question",
      "prompt": "화면에서 무엇을 보았어?",
      "expected_keywords": ["예상", "키워드"]
    }
  }
}
```

## AI-1 입력 계약

AI-1에서 집중 저하 또는 인지 부하 점수를 계산하면 AI Nudge 모듈은 다음 값을 받는 것을 가정합니다.

```json
{
  "cls_score": 0.6,
  "current_time": 22,
  "child_age": 4,
  "speech_available": false
}
```

현재 CLS 기준:

```text
cls_score < 0.5
→ 개입하지 않음

0.5 <= cls_score < 0.7
→ soft nudge

cls_score >= 0.7
→ strong nudge
→ 영상 일시정지 가능
```

## 프론트엔드 전달 형식

최종적으로 프론트엔드에 전달할 Nudge Event 형식은 다음을 기준으로 합니다.

```json
{
  "should_nudge": true,
  "trigger_strength": "soft",
  "cls_score": 0.6,
  "child_tier": "tier2",
  "current_time": 22,
  "mission_type": "choice",
  "nudge_text": "방금 나온 동물은 누구일까요?",
  "pause_video": false,
  "source": "mission_queue",
  "context_source": "previous",
  "scene_summary": "영상 장면 요약"
}
```

프론트엔드 처리 기준:

- `should_nudge`: Nudge UI 표시 여부
- `nudge_text`: 캐릭터 말풍선 또는 음성 출력
- `mission_type`: 미션 UI 종류
- `pause_video`: YouTube 영상 일시정지 여부
- `trigger_strength`: 개입 강도

현재 AI Nudge용 FastAPI 엔드포인트와 프론트엔드 호출 코드는 아직 연결되지 않았습니다.

## 테스트

테스트는 백엔드 루트에서 `python -m` 방식으로 실행합니다.

자막 맥락 선택:

```powershell
python -m tests.ai.nudge.test_caption_slicer
```

백엔드의 모든 mock 자막 형식 확인:

```powershell
python -m tests.ai.nudge.test_mock_subtitles
```

Mock 미션 사전 생성 및 Queue 확인:

```powershell
python -m tests.ai.nudge.test_prefetch_queue --multi
```

실제 Gemini 미션 생성:

```powershell
python -m tests.ai.nudge.test_mock_gemini
```

실제 mock 자막과 Gemini 및 Mission Queue 통합:

```powershell
python -m tests.ai.nudge.test_mock_prefetch
```

Gemini를 호출하는 테스트는 실제 API 사용량이 발생할 수 있습니다.

## 현재 검증된 통합 흐름

다음 흐름은 실제 `subtitle_pinkfong.json`과 Gemini API를 사용해 검증했습니다.

```text
mock_data/subtitle_pinkfong.json
→ 현재 시간 기준 자막 맥락 선택
→ Gemini 티어별 미션 생성
→ Mission Queue 저장
```

FastAPI 엔드포인트와 프론트엔드 연결은 다음 통합 단계에서 진행합니다.