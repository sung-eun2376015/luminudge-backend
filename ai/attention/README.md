# Attention Module (AI-1)

프론트엔드의 AI-1이 계산한 CLS(Cognitive Load Score) 결과를 백엔드에서
검증하기 위한 공통 입력 스키마를 제공합니다.

## 파일 구성

- `schemas.py`: 프론트엔드에서 백엔드로 전달하는 `ClsPayload` Pydantic 모델

## API 연결

Attention 결과는 세션 문맥과 함께 다음 API로 전송합니다.

```http
POST /sessions/{session_id}/nudge
```

이 엔드포인트는 `ClsPayload`를 검증하고 Attention 이벤트를 저장한 다음,
`none`, `soft`, `strong` 강도에 따라 Nudge 응답을 생성합니다.

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

기존의 `POST /attention/cls` 수신 전용 엔드포인트는 Nudge 파이프라인과
연결되지 않는 중복 경로였으므로 제거되었습니다.
