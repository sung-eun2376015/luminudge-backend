from pydantic import BaseModel, Field
from typing import Literal

class ClsPayload(BaseModel):
    cls_score: float = Field(ge=0.0, le=1.0)
    intensity: Literal["none", "soft", "strong"]
    gv: float
    fd: float
    br: int
    timestamp: int
    video_duration_sec: float = Field(gt=0, description="현재 재생 중인 영상의 총 길이(초)")
    cooldown_ms: int = Field(ge=0, description="이 nudge에 적용된 쿨다운 값(ms), 영상 길이 기반 적응형 계산 결과")