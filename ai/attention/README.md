# Attention Module (AI-1)

프론트엔드(브라우저)에서 MediaPipe로 계산한 CLS(Cognitive Load Score) 값을
백엔드가 받아서 검증하는 모듈입니다.

## 담당 범위
- 실시간 CLS 계산(GV/FD/BR, MediaPipe)은 **프론트엔드**에서 처리합니다
  (No-Capture Privacy 원칙에 따라 영상 프레임은 서버로 전송하지 않습니다).
- 이 모듈은 프론트에서 넘어온 CLS 결과값을 받는 API 엔드포인트만 제공합니다.

## 파일 구성
- `schemas.py` — 프론트→백엔드로 전달되는 CLS payload의 pydantic 검증 모델
- `router.py` — `/attention/cls` 엔드포인트 정의

## 사용 방법 (main.py에 연결 필요)
```python
from ai.attention.router import router as attention_router
app.include_router(attention_router)
```

## 엔드포인트

### POST /attention/cls
프론트엔드에서 CLS 이벤트(쿨다운 통과한 실제 nudge 트리거)를 받습니다.

**요청 예시:**
```json
{
  "cls_score": 0.62,
  "intensity": "soft",
  "gv": 0.00012,
  "fd": 3200,
  "br": 4,
  "timestamp": 1731234567890
}
```

## 현재 상태 (2026-07 기준)
- [x] CLS payload 스키마 정의
- [x] 엔드포인트 스켈레톤 (검증 + echo만, 실제 저장/미션 연동 로직 없음)
- [ ] main.py 연결 (Dev 담당)
- [ ] nudge_trigger.py(AI-2)와의 실제 파이프라인 연결 — 4주차 통합 예정