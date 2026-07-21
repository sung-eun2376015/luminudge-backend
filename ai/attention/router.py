# ai/attention/router.py
from fastapi import APIRouter
from ai.attention.schemas import ClsPayload

# attention 관련 API들을 묶어줄 라우터 생성
router = APIRouter(prefix="/api/attention", tags=["Attention/Signal"])

@router.post("/nudge")
async def receive_nudge_report(payload: ClsPayload):
    # TODO: 추후 미션 생성 및 리포트 저장 로직 연동 지점
    print(f"Received Nudge Event from Frontend: {payload}")
    
    return {
        "status": "success",
        "received": {
            "cls_score": payload.cls_score,
            "intensity": payload.intensity,
            "timestamp": payload.timestamp
        }
    }