from pydantic import BaseModel, Field
from typing import Literal


class ClsPayload(BaseModel):
    cls_score: float = Field(ge=0.0, le=1.0)
    intensity: Literal["none", "soft", "strong"]
    gv: float = Field(ge=0)
    fd: float = Field(ge=0)
    br: int = Field(ge=0)
    timestamp: float = Field(ge=0, description="현재 영상 재생 위치(초)")
    video_duration_sec: float = Field(gt=0, description="현재 재생 중인 영상의 총 길이(초)")
    cooldown_ms: int = Field(
        ge=0,
        description="프론트에서 적용한 쿨다운 값(ms). 백엔드는 리포트용으로 저장만 합니다.",
    )
